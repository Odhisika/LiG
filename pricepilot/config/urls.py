from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/suppliers/", include("apps.suppliers.urls")),
    path("api/products/", include("apps.products.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/history/", include("apps.history.urls")),
    path("api/pricing-rules/", include("apps.pricing.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/discoveries/", include("apps.discovery.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # PricePilot web dashboard (not API)
    path("pricing/", include(("apps.pricing.urls_web", "pricing_web"), namespace="pricing-web")),
]
