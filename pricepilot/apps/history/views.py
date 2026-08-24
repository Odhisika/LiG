from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.history.serializers import PriceHistorySerializer
from apps.history.services import HistoryService


class HistoryListView(APIView):
    """GET /api/history/ — list the current user's change history.

    Filters: ?product=<uuid>, ?date_from=<ISO date/datetime>, ?date_to=<ISO date/datetime>.
    """

    serializer_class = PriceHistorySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("product", str, required=False),
            OpenApiParameter("date_from", str, required=False),
            OpenApiParameter("date_to", str, required=False),
        ],
        responses=PriceHistorySerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        entries = HistoryService.list_for_owner(
            request.user,
            product_id=request.query_params.get("product"),
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(envelope(data=PriceHistorySerializer(entries, many=True).data))


class HistoryDetailView(APIView):
    """GET /api/history/{id}/ — one history entry, scoped to the current user."""

    serializer_class = PriceHistorySerializer

    @extend_schema(responses=PriceHistorySerializer)
    def get(self, request: Request, history_id) -> Response:
        entry = HistoryService.get_for_owner(request.user, history_id)
        return Response(envelope(data=PriceHistorySerializer(entry).data))
