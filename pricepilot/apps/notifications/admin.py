from django.contrib import admin

from apps.notifications.models import NotificationEvent


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "owner", "product", "sent", "sent_at", "created_at"]
    list_filter = ["event_type", "sent"]
    search_fields = ["owner__email", "product__name"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
