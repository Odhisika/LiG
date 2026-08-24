from django.urls import path

from apps.pricing.views import PriceHistoryDashboardView, StockAlertsDashboardView

app_name = "pricing_web"

urlpatterns = [
    path("", PriceHistoryDashboardView.as_view(), name="dashboard"),
    path("stock-alerts/", StockAlertsDashboardView.as_view(), name="stock-alerts"),
]
