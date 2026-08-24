from django.urls import path

from apps.products.views import (
    ProductCategoriesView,
    ProductDetailView,
    ProductListCreateView,
)

app_name = "products"

urlpatterns = [
    path("", ProductListCreateView.as_view(), name="list-create"),
    path("categories/", ProductCategoriesView.as_view(), name="categories"),
    path("<uuid:product_id>/", ProductDetailView.as_view(), name="detail"),
]
