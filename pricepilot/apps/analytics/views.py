from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.serializers import AnalyticsSummarySerializer
from apps.analytics.services import AnalyticsService
from apps.common.api import envelope


class AnalyticsSummaryView(APIView):
    """GET /api/analytics/summary/ — aggregate stats over the current
    user's price change history.

    Filters: ?days=<int, default 30> lookback window, ?limit=<int,
    default 10> for each top-N list (1-100).
    """

    serializer_class = AnalyticsSummarySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("days", int, required=False),
            OpenApiParameter("limit", int, required=False),
        ],
        responses=AnalyticsSummarySerializer,
    )
    def get(self, request: Request) -> Response:
        days = int(request.query_params.get("days", 30))
        limit = int(request.query_params.get("limit", 10))
        summary = AnalyticsService.get_summary(request.user, days=days, limit=limit)
        return Response(envelope(data=AnalyticsSummarySerializer(summary).data))
