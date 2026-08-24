from django.contrib import admin

from apps.discovery.models import DiscoveredProduct


@admin.register(DiscoveredProduct)
class DiscoveredProductAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "supplier", "price", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "url", "owner__email", "supplier__name"]
