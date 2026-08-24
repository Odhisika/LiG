from django.contrib import admin

from apps.suppliers.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "currency", "is_active", "created_at"]
    list_filter = ["currency", "is_active"]
    search_fields = ["name", "website", "owner__email"]
