from django.urls import path

from apps.suppliers.views import SupplierDetailView, SupplierListCreateView

app_name = "suppliers"

urlpatterns = [
    path("", SupplierListCreateView.as_view(), name="list-create"),
    path("<uuid:supplier_id>/", SupplierDetailView.as_view(), name="detail"),
]
