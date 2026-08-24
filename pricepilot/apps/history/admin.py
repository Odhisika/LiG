from django.contrib import admin

from apps.history.models import PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "owner",
        "old_price",
        "new_price",
        "old_stock",
        "new_stock",
        "reason",
        "created_at",
    ]
    list_filter = ["reason", "price_changed", "stock_changed"]
    search_fields = ["product__name", "owner__email"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
