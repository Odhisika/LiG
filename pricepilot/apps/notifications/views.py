from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.notifications.models import NotificationEvent
from apps.notifications.serializers import NotificationEventSerializer


class NotificationEventListView(APIView):
    """GET /api/notifications/ — the current user's notification events.

    Filters: ?event_type=<type>, ?sent=<true|false>. Read-only — events
    are created exclusively by PriceMonitorService and the scheduler's
    failure handling, never through this API.
    """

    serializer_class = NotificationEventSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("event_type", str, required=False),
            OpenApiParameter("sent", bool, required=False),
        ],
        responses=NotificationEventSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        qs = NotificationEvent.objects.filter(owner=request.user)

        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        sent = request.query_params.get("sent")
        if sent is not None:
            qs = qs.filter(sent=sent.lower() == "true")

        return Response(envelope(data=NotificationEventSerializer(qs, many=True).data))
