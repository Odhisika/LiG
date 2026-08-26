import logging
import json
from datetime import timedelta

from django.db import models
from django.db.models import Avg, Count, Max, Min
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api import envelope
from apps.history.models import PriceHistory
from apps.notifications.models import NotificationEvent
from apps.products.models import Product
from apps.pricing.serializers import (
    DefaultMarkupSerializer,
    PricingRuleSerializer,
)
from apps.pricing.services import (
    DefaultMarkupService,
    PricingRuleService,
)
from apps.sync.services import StoreSyncService

logger = logging.getLogger(__name__)


class PricingRuleListCreateView(APIView):
    """GET  /api/pricing-rules/  — list the current user's pricing rules.
    POST /api/pricing-rules/  — create a rule with its ordered steps.
    """

    serializer_class = PricingRuleSerializer

    @extend_schema(responses=PricingRuleSerializer(many=True))
    def get(self, request: Request) -> Response:
        rules = PricingRuleService.list_for_owner(request.user)
        return Response(envelope(data=PricingRuleSerializer(rules, many=True).data))

    @extend_schema(request=PricingRuleSerializer, responses=PricingRuleSerializer)
    def post(self, request: Request) -> Response:
        rule = PricingRuleService.create(request.user, request.data)
        return Response(
            envelope(data=PricingRuleSerializer(rule).data),
            status=status.HTTP_201_CREATED,
        )


class PricingRuleDetailView(APIView):
    """GET/PATCH/DELETE /api/pricing-rules/{id}/ — scoped to the current user."""

    serializer_class = PricingRuleSerializer

    @extend_schema(responses=PricingRuleSerializer)
    def get(self, request: Request, rule_id) -> Response:
        rule = PricingRuleService.get_for_owner(request.user, rule_id)
        return Response(envelope(data=PricingRuleSerializer(rule).data))

    @extend_schema(request=PricingRuleSerializer, responses=PricingRuleSerializer)
    def patch(self, request: Request, rule_id) -> Response:
        rule = PricingRuleService.update(
            request.user, rule_id, request.data, partial=True, sync_lig=True
        )
        return Response(envelope(data=PricingRuleSerializer(rule).data))

    @extend_schema(responses=None)
    def delete(self, request: Request, rule_id) -> Response:
        PricingRuleService.delete(request.user, rule_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DefaultMarkupView(APIView):
    """GET/PUT /api/pricing/default-markup/ — the merchant's single default
    markup % applied to products that don't have their own pricing rule
    (and no manual selling price). Setting it reprices the store on the
    next sync.
    """

    serializer_class = DefaultMarkupSerializer

    @extend_schema(responses=DefaultMarkupSerializer)
    def get(self, request: Request) -> Response:
        markup = DefaultMarkupService.get_for_owner(request.user)
        percent = markup.markup_percent if markup is not None and markup.is_active else None
        return Response(
            envelope(data=DefaultMarkupSerializer({"markup_percent": percent}).data)
        )

    @extend_schema(request=DefaultMarkupSerializer, responses=DefaultMarkupSerializer)
    def put(self, request: Request) -> Response:
        serializer = DefaultMarkupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                envelope(error={"message": "Invalid input.", "detail": serializer.errors}),
                status=status.HTTP_400_BAD_REQUEST,
            )

        markup, affected = DefaultMarkupService.set_markup(
            request.user, serializer.validated_data["markup_percent"]
        )
        synced = StoreSyncService.sync_all(
            Product.objects.filter(
                owner=request.user,
                pricing_rule__isnull=True,
                selling_price__isnull=True,
                store_product_id__isnull=False,
            )
        )
        logger.info(
            "Default markup updated for user %s; sync result=%s",
            request.user.id,
            synced,
        )
        return Response(
            envelope(
                data=DefaultMarkupSerializer(
                    {"markup_percent": markup.markup_percent, "affected_products": affected}
                ).data
            )
        )


class PriceHistoryDashboardView(TemplateView):
    """Renders the price history dashboard page with embedded data."""

    template_name = "pricing/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Price History Dashboard"

        # Preload data for the template
        user = self.request.user
        if user.is_authenticated:
            context["api_token"] = self._get_token(user)
        else:
            context["api_token"] = ""

        return context

    def _get_token(self, user):
        """Generate or retrieve a token for API access."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class PriceHistoryAPIView(APIView):
    """Returns price history data as JSON for chart rendering."""

    def get(self, request: Request) -> Response:
        # Get query parameters
        days = int(request.query_params.get("days", 30))
        product_id = request.query_params.get("product_id")
        category = request.query_params.get("category")

        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Base queryset
        qs = PriceHistory.objects.filter(
            created_at__gte=start_date,
            owner=request.user,
            price_changed=True,
        )

        # Apply filters
        if product_id:
            qs = qs.filter(product_id=product_id)
        if category:
            qs = qs.filter(product__category=category)

        # Aggregate daily price data
        daily_data = (
            qs.extra(select={"date": "DATE(created_at)"})
            .values("date")
            .annotate(
                avg_old_price=Avg("old_price"),
                avg_new_price=Avg("new_price"),
                price_changes=Count("id"),
            )
            .order_by("date")
        )

        # Category summary with margin calculation
        category_summary = (
            qs.values("product__category")
            .annotate(
                avg_old=Avg("old_price"),
                avg_new=Avg("new_price"),
                product_count=Count("product", distinct=True),
                changes=Count("id"),
            )
            .order_by("-changes")
        )

        # Calculate margin for each category
        for cat in category_summary:
            if cat["avg_old"] and cat["avg_old"] > 0 and cat["avg_new"]:
                cat["avg_margin"] = float((cat["avg_new"] - cat["avg_old"]) / cat["avg_old"] * 100)
            else:
                cat["avg_margin"] = 0

        # Top price increases (new > old = price went up, good for margins)
        top_increases = (
            qs.filter(new_price__gt=models.F("old_price"))
            .order_by("-new_price")[:5]
            .values(
                "product__name",
                "old_price",
                "new_price",
            )
        )

        # Calculate margin for increases
        for item in top_increases:
            if item["old_price"] and item["old_price"] > 0:
                item["margin_percent"] = float((item["new_price"] - item["old_price"]) / item["old_price"] * 100)
            else:
                item["margin_percent"] = 0

        # Top price decreases (new < old = price went down)
        top_decreases = (
            qs.filter(new_price__lt=models.F("old_price"))
            .order_by("new_price")[:5]
            .values(
                "product__name",
                "old_price",
                "new_price",
            )
        )

        # Calculate margin for decreases
        for item in top_decreases:
            if item["old_price"] and item["old_price"] > 0:
                item["margin_percent"] = float((item["new_price"] - item["old_price"]) / item["old_price"] * 100)
            else:
                item["margin_percent"] = 0

        # Stats
        stats = {
            "total_price_changes": qs.count(),
            "products_affected": qs.values("product").distinct().count(),
            "avg_margin": None,
            "min_margin": None,
            "max_margin": None,
        }

        # Calculate margin stats
        margins = []
        for item in qs.filter(new_price__gt=0).values("old_price", "new_price"):
            if item["old_price"] and item["old_price"] > 0:
                margin = float((item["new_price"] - item["old_price"]) / item["old_price"] * 100)
                margins.append(margin)

        if margins:
            stats["avg_margin"] = sum(margins) / len(margins)
            stats["min_margin"] = min(margins)
            stats["max_margin"] = max(margins)

        # Convert to JSON-serializable format
        chart_data = {
            "daily": list(daily_data),
            "categories": list(category_summary),
            "top_increases": list(top_increases),
            "top_decreases": list(top_decreases),
            "stats": stats,
        }

        return Response(envelope(data=chart_data))


class StockAlertsDashboardView(TemplateView):
    """Renders the stock alerts dashboard page with embedded data."""

    template_name = "pricing/stock_alerts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Stock Alerts & Reorder"

        user = self.request.user
        if user.is_authenticated:
            context["api_token"] = self._get_token(user)
        else:
            context["api_token"] = ""

        return context

    def _get_token(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class StockAlertsAPIView(APIView):
    """Returns stock alert data as JSON for the dashboard."""

    def get(self, request: Request) -> Response:
        from apps.products.models import Product

        # Get low-stock products (stock > 0 but <= threshold)
        low_stock = Product.objects.filter(
            owner=request.user,
            stock__isnull=False,
            stock__gt=0,
            stock__lte=10,
            status=Product.Status.ACTIVE,
        ).values(
            "id", "name", "stock", "category", "supplier__name", "supplier_url"
        ).order_by("stock")

        # Get out-of-stock products
        out_of_stock = Product.objects.filter(
            owner=request.user,
            status=Product.Status.OUT_OF_STOCK,
        ).values(
            "id", "name", "category", "supplier__name", "supplier_url"
        )

        # Get products that were recently restocked (had low stock events)
        recent_alerts = (
            NotificationEvent.objects.filter(
                owner=request.user,
                event_type__in=[
                    NotificationEvent.EventType.LOW_STOCK,
                    NotificationEvent.EventType.OUT_OF_STOCK,
                ],
            )
            .select_related("product")
            .order_by("-created_at")[:20]
        )

        alerts_list = []
        for alert in recent_alerts:
            alerts_list.append({
                "product_name": alert.product.name if alert.product else "Unknown",
                "event_type": alert.event_type,
                "stock": alert.payload.get("stock"),
                "created_at": alert.created_at.isoformat(),
                "sent": alert.sent,
            })

        # Stats
        stats = {
            "low_stock_count": low_stock.count(),
            "out_of_stock_count": out_of_stock.count(),
            "total_alerts": len(alerts_list),
            "unsent_alerts": NotificationEvent.objects.filter(
                owner=request.user,
                event_type__in=[
                    NotificationEvent.EventType.LOW_STOCK,
                    NotificationEvent.EventType.OUT_OF_STOCK,
                ],
                sent=False,
            ).count(),
        }

        # Category breakdown for low stock
        category_breakdown = (
            low_stock.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        data = {
            "stats": stats,
            "low_stock": list(low_stock),
            "out_of_stock": list(out_of_stock),
            "recent_alerts": alerts_list,
            "categories": list(category_breakdown),
        }

        return Response(envelope(data=data))
