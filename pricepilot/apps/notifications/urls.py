from django.urls import path

from apps.notifications.views import NotificationEventListView

app_name = "notifications"

urlpatterns = [
    path("", NotificationEventListView.as_view(), name="list"),
]
