from django.urls import path

from apps.history.views import HistoryDetailView, HistoryListView

app_name = "history"

urlpatterns = [
    path("", HistoryListView.as_view(), name="list"),
    path("<uuid:history_id>/", HistoryDetailView.as_view(), name="detail"),
]
