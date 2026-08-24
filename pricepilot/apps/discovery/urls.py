from django.urls import path

from apps.discovery.views import (
    DiscoveredProductDismissView,
    DiscoveredProductImportView,
    DiscoveredProductListView,
)

app_name = "discovery"

urlpatterns = [
    path("", DiscoveredProductListView.as_view(), name="list"),
    path("<uuid:discovery_id>/import/", DiscoveredProductImportView.as_view(), name="import"),
    path("<uuid:discovery_id>/dismiss/", DiscoveredProductDismissView.as_view(), name="dismiss"),
]
