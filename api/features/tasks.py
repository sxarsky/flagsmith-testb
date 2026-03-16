import logging
from typing import Any

from task_processor.decorators import (
    register_task_handler,
)

from environments.models import Webhook
from features.models import Feature, FeatureState
from features.multivariate.models import MultivariateFeatureStateValue
from webhooks.constants import WEBHOOK_DATETIME_FORMAT
from webhooks.tasks import (
    call_environment_webhooks,
    call_organisation_webhooks,
)
from webhooks.webhooks import WebhookEventType

from .models import HistoricalFeatureState  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


def trigger_feature_state_change_webhooks(  # type: ignore[no-untyped-def]
    instance: FeatureState, event_type: WebhookEventType = WebhookEventType.FLAG_UPDATED
):
    assert event_type in [WebhookEventType.FLAG_UPDATED, WebhookEventType.FLAG_DELETED]

    history_instance = instance.history.first()
    timestamp = (
        history_instance.history_date.strftime(WEBHOOK_DATETIME_FORMAT)
        if history_instance and history_instance.history_date
        else ""
    )
    changed_by = (
        history_instance.history_user.email
        if history_instance and history_instance.history_user
        else (
            history_instance.master_api_key.name
            if history_instance and history_instance.master_api_key
            else ""
        )
    )
    new_state = (
        None
        if event_type == WebhookEventType.FLAG_DELETED
        else _get_feature_state_webhook_data(instance)
    )
    data = {"new_state": new_state, "changed_by": changed_by, "timestamp": timestamp}
    previous_state = _get_previous_state(instance, history_instance, event_type)

    if previous_state:
        data.update(previous_state=previous_state)

    call_environment_webhooks.delay(
        args=(instance.environment.id, data, event_type.value)  # type: ignore[union-attr]
    )

    call_organisation_webhooks.delay(
        args=(
            instance.environment.project.organisation.id,  # type: ignore[union-attr]
            data,
            event_type.value,
        )
    )


def _get_previous_state(
    instance: FeatureState,
    history_instance: HistoricalFeatureState,
    event_type: WebhookEventType,
) -> dict[str, Any] | None:
    if event_type == WebhookEventType.FLAG_DELETED:
        return _get_feature_state_webhook_data(instance)

    # Change requests create a new FeatureState with its own history
    if instance.change_request_id is not None:
        previous_fs = _get_previous_feature_state_for_change_request(instance)
        if previous_fs:
            return _get_feature_state_webhook_data(previous_fs)
        return None

    if history_instance and history_instance.prev_record:
        return _get_feature_state_webhook_data(
            history_instance.prev_record.instance, previous=True
        )
    return None


def _get_previous_feature_state_for_change_request(
    instance: FeatureState,
) -> FeatureState | None:
    """Find the previous live FeatureState for a change request (legacy versioning)."""
    result: FeatureState | None = (
        FeatureState.objects.exclude(
            change_request_id=instance.change_request_id,
        )
        .filter(
            environment_id=instance.environment_id,
            feature_id=instance.feature_id,
            feature_segment=instance.feature_segment,
            identity=instance.identity,
            version__isnull=False,
            live_from__lt=instance.live_from,
        )
        .order_by("-live_from")
        .select_related(
            "feature",
            "environment",
            "feature_state_value",
            "feature_segment",
            "identity",
        )
        .first()
    )
    return result


def _get_feature_state_webhook_data(
    feature_state: FeatureState,
    previous: bool = False,
) -> dict[str, Any]:
    if previous:
        value = feature_state.previous_feature_state_value
        mv_values = _get_previous_multivariate_values(feature_state)
    else:
        value = feature_state.get_feature_state_value()
        mv_values = list(
            feature_state.multivariate_feature_state_values.select_related(
                "multivariate_feature_option"
            ).all()
        )

    assert feature_state.environment is not None
    return Webhook.generate_webhook_feature_state_data(
        feature_state.feature,
        environment=feature_state.environment,
        enabled=feature_state.enabled,
        value=value,
        identity_id=feature_state.identity_id,
        identity_identifier=getattr(feature_state.identity, "identifier", None),
        feature_segment=feature_state.feature_segment,
        multivariate_feature_state_values=mv_values,
    )


def _get_previous_multivariate_values(
    feature_state: FeatureState,
) -> list[MultivariateFeatureStateValue]:
    """Get previous multivariate values from history."""
    mv_values: list[MultivariateFeatureStateValue] = []
    for mv in MultivariateFeatureStateValue.objects.filter(
        feature_state_id=feature_state.id
    ).select_related("multivariate_feature_option"):
        history = mv.history.first()
        if history and history.prev_record:
            mv_values.append(history.prev_record.instance)
    return mv_values


@register_task_handler()
def delete_feature(feature_id: int) -> None:
    Feature.objects.get(pk=feature_id).delete()


@register_task_handler()
def check_feature_health() -> None:
    """
    Periodic task to check feature health across all environments.
    Runs hourly to update health scores and detect zombie flags.
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import Feature, FeatureHealthStatus
    from environments.models import Environment
    
    # Get all features and environments
    features = Feature.objects.filter(is_archived=False)
    environments = Environment.objects.all()
    
    for feature in features:
        for environment in environments.filter(project=feature.project):
            # Get or create health status
            health_status, created = FeatureHealthStatus.objects.get_or_create(
                feature=feature,
                environment=environment,
            )
            
            # Calculate days since last change
            if feature.feature_states.filter(environment=environment).exists():
                last_change = feature.feature_states.filter(
                    environment=environment
                ).order_by('-updated_at').first()
                
                if last_change:
                    days_since_change = (timezone.now() - last_change.updated_at).days
                    health_status.days_since_last_change = days_since_change
            
            # Check if flag is a zombie (not evaluated in 30+ days)
            if health_status.last_evaluated:
                days_since_eval = (timezone.now() - health_status.last_evaluated).days
                health_status.is_zombie = days_since_eval > 30
            else:
                health_status.is_zombie = True
            
            # Calculate health score
            score = 100
            
            # Reduce score based on error rate
            if health_status.evaluation_error_rate > 0.05:
                score -= 30
            elif health_status.evaluation_error_rate > 0.01:
                score -= 15
            
            # Reduce score for zombie flags
            if health_status.is_zombie:
                score -= 40
            
            # Reduce score based on days since last change
            if health_status.days_since_last_change > 90:
                score -= 20
            elif health_status.days_since_last_change > 60:
                score -= 10
            
            health_status.health_score = max(0, min(100, score))
            
            # Trigger alert if health score drops below threshold
            if health_status.health_score < 80:
                health_status.alert_triggered = True
            
            health_status.save()
    
    logger.info(f"Feature health check completed for {features.count()} features across {environments.count()} environments")
