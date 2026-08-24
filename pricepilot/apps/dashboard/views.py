from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.dashboard.serializers import DashboardSummarySerializer
from apps.dashboard.services import DashboardService


class DashboardSummaryView(APIView):
    """GET /api/dashboard/summary/ — headline counts for the current user.

    `products_changed_today`, `stock_changes_today`, `failed_scrapes_today`,
    `todays_checks`, and `recent_activity` are honest zero/empty values
    until Phase 2's History/ScrapeLog models exist to back them — see
    DashboardService for details.
    """

    serializer_class = DashboardSummarySerializer

    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request: Request) -> Response:
        summary = DashboardService.get_summary(request.user)
        return Response(envelope(data=DashboardSummarySerializer(summary).data))
