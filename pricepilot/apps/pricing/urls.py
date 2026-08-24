from django.urls import path

from apps.pricing.views import (
    DefaultMarkupView,
    PriceHistoryAPIView,
    PriceHistoryDashboardView,
    PricingRuleDetailView,
    PricingRuleListCreateView,
    StockAlertsAPIView,
    StockAlertsDashboardView,
)

app_name = "pricing"

urlpatterns = [
    path("", PricingRuleListCreateView.as_view(), name="list-create"),
    path("default-markup/", DefaultMarkupView.as_view(), name="default-markup"),
    path("<uuid:rule_id>/", PricingRuleDetailView.as_view(), name="detail"),
    path("dashboard/", PriceHistoryDashboardView.as_view(), name="dashboard"),
    path("stock-alerts/", StockAlertsDashboardView.as_view(), name="stock-alerts"),
    path("api/history/", PriceHistoryAPIView.as_view(), name="price-history-api"),
    path("api/stock-alerts/", StockAlertsAPIView.as_view(), name="stock-alerts-api"),
]
