from drf_spectacular.utils import extend_schema
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from apps.common.api import envelope
from apps.dashboard.models import ActivityEvent
from apps.dashboard.serializers import ActivityEventSerializer, DashboardSummarySerializer
from apps.dashboard.services import DashboardService


class DashboardSummaryView(APIView):
    """GET /api/dashboard/summary/ — headline counts for the current user."""

    serializer_class = DashboardSummarySerializer

    @extend_schema(responses=DashboardSummarySerializer)
    def get(self, request: Request) -> Response:
        summary = DashboardService.get_summary(request.user)
        return Response(envelope(data=DashboardSummarySerializer(summary).data))


class ActivityFeedPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class ActivityFeedView(APIView):
    """GET /api/dashboard/activity/ — full activity feed with filters.

    Query params:
      event_type  — filter by EventType choice
      product     — filter by product UUID
      supplier    — filter by supplier UUID
      date_from   — ISO date, inclusive
      date_to     — ISO date, inclusive
    Paginated with 25 items per page.
    """

    pagination_class = ActivityFeedPagination

    @extend_schema(
        parameters=[
            {"name": "event_type", "type": "str", "required": False},
            {"name": "product", "type": "str", "required": False},
            {"name": "supplier", "type": "str", "required": False},
            {"name": "date_from", "type": "str", "required": False},
            {"name": "date_to", "type": "str", "required": False},
        ],
        responses=ActivityEventSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        from django.utils.dateparse import parse_date

        qs = ActivityEvent.objects.filter(owner=request.user).select_related(
            "product", "supplier"
        )

        event_type = request.query_params.get("event_type")
        if event_type:
            qs = qs.filter(event_type=event_type)

        product = request.query_params.get("product")
        if product:
            qs = qs.filter(product_id=product)

        supplier = request.query_params.get("supplier")
        if supplier:
            qs = qs.filter(supplier_id=supplier)

        date_from = request.query_params.get("date_from")
        if date_from:
            parsed = parse_date(date_from)
            if parsed:
                qs = qs.filter(created_at__date__gte=parsed)

        date_to = request.query_params.get("date_to")
        if date_to:
            parsed = parse_date(date_to)
            if parsed:
                qs = qs.filter(created_at__date__lte=parsed)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        serializer = ActivityEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
