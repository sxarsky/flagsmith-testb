"""
Feature Budget Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import FeatureBudget
from .serializers import FeatureBudgetSerializer, FeatureBudgetStatusSerializer
from features.models import Feature


class FeatureBudgetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing feature budgets.

    Provides CRUD operations and reset functionality.
    """

    serializer_class = FeatureBudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter budgets by feature if feature_id is provided."""
        queryset = FeatureBudget.objects.select_related('feature').all()

        feature_id = self.request.query_params.get('feature_id')
        if feature_id:
            queryset = queryset.filter(feature_id=feature_id)

        return queryset

    @action(detail=True, methods=['post'])
    def reset(self, request, pk=None):
        """
        Reset the monthly counter for a budget.

        POST /api/v1/budgets/{id}/reset/
        """
        budget = self.get_object()
        budget.reset_monthly_counter()

        serializer = self.get_serializer(budget)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], serializer_class=FeatureBudgetStatusSerializer)
    def status(self, request, pk=None):
        """
        Get current budget status with usage statistics.

        GET /api/v1/budgets/{id}/status/
        """
        budget = self.get_object()
        budget.check_and_reset_if_needed()

        serializer = FeatureBudgetStatusSerializer(budget)
        return Response(serializer.data)
