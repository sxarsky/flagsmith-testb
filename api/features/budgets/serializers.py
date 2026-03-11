"""
Feature Budget Serializers
"""

from rest_framework import serializers
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import FeatureBudget


class FeatureBudgetSerializer(serializers.ModelSerializer):
    """Serializer for FeatureBudget model."""

    usage_percentage = serializers.ReadOnlyField()
    remaining_evaluations = serializers.ReadOnlyField()
    feature_name = serializers.CharField(source='feature.name', read_only=True)

    class Meta:
        model = FeatureBudget
        fields = [
            'id',
            'feature',
            'feature_name',
            'evaluation_limit',
            'current_count',
            'reset_date',
            'limit_exceeded_action',
            'limit_exceeded',
            'usage_percentage',
            'remaining_evaluations',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['current_count', 'limit_exceeded', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create budget with automatic reset_date if not provided."""
        if 'reset_date' not in validated_data:
            # Set reset date to first day of next month
            today = date.today()
            next_month = today + relativedelta(months=1)
            validated_data['reset_date'] = next_month.replace(day=1)

        return super().create(validated_data)


class FeatureBudgetStatusSerializer(serializers.ModelSerializer):
    """Read-only serializer for budget status."""

    usage_percentage = serializers.ReadOnlyField()
    remaining_evaluations = serializers.ReadOnlyField()
    feature_name = serializers.CharField(source='feature.name', read_only=True)
    days_until_reset = serializers.SerializerMethodField()

    class Meta:
        model = FeatureBudget
        fields = [
            'id',
            'feature_name',
            'evaluation_limit',
            'current_count',
            'usage_percentage',
            'remaining_evaluations',
            'limit_exceeded',
            'reset_date',
            'days_until_reset',
            'limit_exceeded_action',
        ]

    def get_days_until_reset(self, obj):
        """Calculate days until next reset."""
        today = date.today()
        if obj.reset_date > today:
            return (obj.reset_date - today).days
        return 0
