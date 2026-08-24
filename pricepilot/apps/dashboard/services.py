from decimal import Decimal

from django.db.models import Count

from apps.accounts.models import User
from apps.products.models import Product
from apps.suppliers.models import Supplier


class DashboardService:
    """Read-only aggregation over Product/Supplier (and, from Phase 2,
    History/ScrapeLog) for the current user. No models of its own —
    this is intentionally a pure query layer.
    """

    @staticmethod
    def _products_by_status(owner: User) -> dict[str, int]:
        counts = {choice.value: 0 for choice in Product.Status}
        rows = Product.objects.filter(owner=owner).values("status").annotate(count=Count("id"))
        for row in rows:
            counts[row["status"]] = row["count"]
        return counts

    @staticmethod
    def _products_by_category(owner: User) -> list[dict]:
        rows = (
            Product.objects.filter(owner=owner)
            .exclude(category="")
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count", "category")
        )
        return [{"category": row["category"], "count": row["count"]} for row in rows]

    @staticmethod
    def _average_profit(owner: User) -> Decimal | None:
        """Average margin using the *effective* selling price (manual
        selling_price, else default markup, else supplier price) — so the
        dashboard number matches what the store actually charges.
        """
        from apps.pricing.services import DefaultMarkupService, PricingService

        products = list(
            Product.objects.filter(owner=owner, supplier_price__isnull=False).only(
                "supplier_price", "selling_price", "pricing_rule_id"
            )
        )
        markup = DefaultMarkupService.get_markup_percent(owner)
        margins = []
        for product in products:
            priced = (
                product.selling_price is not None
                or product.pricing_rule_id is not None
                or bool(markup)
            )
            if not priced:
                continue
            effective = PricingService.effective_selling_price(
                product.supplier_price,
                selling_price=product.selling_price,
                markup_percent=markup,
            )
            margins.append(effective - product.supplier_price)
        if not margins:
            return None
        return (sum(margins) / len(margins)).quantize(Decimal("0.01"))

    @staticmethod
    def get_summary(owner: User) -> dict:
        from apps.pricing.services import DefaultMarkupService

        markup = DefaultMarkupService.get_markup_percent(owner)
        return {
            "products_monitored": Product.objects.filter(
                owner=owner, status=Product.Status.ACTIVE
            ).count(),
            "suppliers_count": Supplier.objects.filter(owner=owner, is_active=True).count(),
            "products_by_status": DashboardService._products_by_status(owner),
            "products_by_category": DashboardService._products_by_category(owner),
            "average_profit": DashboardService._average_profit(owner),
            "default_markup": str(markup) if markup is not None else None,
            # --- Phase 2 (History / ScrapeLog) placeholders ---
            "products_changed_today": 0,
            "stock_changes_today": 0,
            "failed_scrapes_today": 0,
            "todays_checks": 0,
            "recent_activity": [],
        }
