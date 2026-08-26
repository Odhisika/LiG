from django.urls import path

from apps.dashboard.views import ActivityFeedView, DashboardSummaryView

app_name = "dashboard"

urlpatterns = [
    path("summary/", DashboardSummaryView.as_view(), name="summary"),
    path("activity/", ActivityFeedView.as_view(), name="activity"),
]
