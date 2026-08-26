from django.contrib import admin

from apps.dashboard.models import ActivityEvent


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "owner", "product", "supplier", "created_at")
    list_filter = ("event_type", "created_at")
    raw_id_fields = ("owner", "product", "supplier")
    readonly_fields = ("owner", "event_type", "product", "supplier", "payload", "created_at")
