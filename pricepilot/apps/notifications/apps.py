from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "apps.notifications"

    def ready(self):
        # Importing each channel module triggers its
        # @NotificationChannelRegistry.register decorator.
        from apps.notifications.channels import email  # noqa: F401
