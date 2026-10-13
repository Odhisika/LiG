from django.contrib import admin

from apps.products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "owner",
        "supplier",
        "status",
        "publish_to_store",
        "use_supplier_images",
        "supplier_price",
        "selling_price",
        "stock",
        "last_checked_at",
    ]
    list_filter = ["status", "publish_to_store", "currency"]
    list_editable = ["publish_to_store", "use_supplier_images"]
    search_fields = ["name", "sku", "owner__email", "supplier__name"]
    actions = ["publish_to_store_action", "unpublish_from_store_action"]

    @admin.action(description="Show selected products on the storefront")
    def publish_to_store_action(self, request, queryset):
        updated = queryset.update(publish_to_store=True)
        self.message_user(request, f"{updated} product(s) will be shown on the storefront.")

    @admin.action(description="Hide selected products from the storefront")
    def unpublish_from_store_action(self, request, queryset):
        updated = queryset.update(publish_to_store=False)
        self.message_user(request, f"{updated} product(s) will be hidden from the storefront.")
