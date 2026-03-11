"""
Feature Budget Models

Track and enforce evaluation limits for feature flags to prevent runaway costs.
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta

from features.models import Feature


class FeatureBudget(models.Model):
    """
    Budget limit configuration for a feature flag.

    Tracks evaluation counts and enforces limits to control costs.
    """

    DISABLE = 'disable'
    ALERT = 'alert'

    LIMIT_EXCEEDED_ACTIONS = [
        (DISABLE, 'Disable Feature'),
        (ALERT, 'Send Alert Only'),
    ]

    feature = models.OneToOneField(
        Feature,
        on_delete=models.CASCADE,
        related_name='budget',
        help_text="Feature this budget applies to"
    )

    evaluation_limit = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Maximum number of evaluations allowed per month"
    )

    current_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Current evaluation count for this period"
    )

    reset_date = models.DateField(
        help_text="Date when the counter resets (next month)"
    )

    limit_exceeded_action = models.CharField(
        max_length=20,
        choices=LIMIT_EXCEEDED_ACTIONS,
        default=ALERT,
        help_text="Action to take when limit is exceeded"
    )

    limit_exceeded = models.BooleanField(
        default=False,
        help_text="Whether the limit has been exceeded in the current period"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'features_featurebudget'
        ordering = ['-created_at']

    def __str__(self):
        return f"Budget for {self.feature.name}: {self.current_count}/{self.evaluation_limit}"

    def increment_count(self):
        """
        Increment the evaluation counter and check if limit exceeded.

        Returns:
            bool: True if limit was exceeded, False otherwise
        """
        self.current_count += 1

        if self.current_count >= self.evaluation_limit and not self.limit_exceeded:
            self.limit_exceeded = True
            self.save()
            return True

        self.save(update_fields=['current_count'])
        return False

    def reset_monthly_counter(self):
        """Reset the counter and set next reset date."""
        self.current_count = 0
        self.limit_exceeded = False
        # Set reset date to first day of next month
        if self.reset_date.month == 12:
            self.reset_date = self.reset_date.replace(year=self.reset_date.year + 1, month=1, day=1)
        else:
            self.reset_date = self.reset_date.replace(month=self.reset_date.month + 1, day=1)
        self.save()

    def check_and_reset_if_needed(self):
        """Check if reset date has passed and reset if needed."""
        today = timezone.now().date()
        if today >= self.reset_date:
            self.reset_monthly_counter()

    @property
    def usage_percentage(self):
        """Calculate percentage of budget used."""
        if self.evaluation_limit == 0:
            return 0
        return (self.current_count / self.evaluation_limit) * 100

    @property
    def remaining_evaluations(self):
        """Calculate remaining evaluations before limit."""
        return max(0, self.evaluation_limit - self.current_count)
