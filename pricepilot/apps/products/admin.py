from django.contrib import admin

from apps.products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "owner",
        "supplier",
        "status",
        "supplier_price",
        "selling_price",
        "stock",
        "last_checked_at",
    ]
    list_filter = ["status", "currency"]
    search_fields = ["name", "sku", "owner__email", "supplier__name"]
