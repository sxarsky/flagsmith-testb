"""
Feature Budget URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import FeatureBudgetViewSet

app_name = "budgets"

router = DefaultRouter()
router.register(r'', FeatureBudgetViewSet, basename='budget')

urlpatterns = [
    path('', include(router.urls)),
]
