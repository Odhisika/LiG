from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.common.models import SoftDeleteModel, TimeStampedModel


class PricingRule(SoftDeleteModel):
    """A named, reusable pricing formula a merchant can assign to any
    number of products. Modeled as an ordered chain of small steps
    (PricingRuleStep) rather than a free-text formula — each step type
    is unambiguous and independently testable, and the whole chain
    covers every example in the blueprint (simple markup, cost-plus,
    FX-adjusted) without needing a formula parser.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pricing_rules"
    )
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_pricing_rule_name_per_owner",
            )
        ]

    def __str__(self) -> str:
        return self.name


class PricingRuleStep(TimeStampedModel):
    """One step in a PricingRule's chain, applied in `order`.

    Semantics (applied to the running price, starting from the
    supplier price):
      MARKUP_PCT  -> price += price * (value / 100)
      FLAT_FEE    -> price += value
      SHIPPING    -> price += value   (kept distinct from FLAT_FEE for
                                        reporting/clarity, same math)
      TAX         -> price += price * (value / 100)
      FX_CONVERT  -> price *= value   (value = exchange rate)
    """

    class StepType(models.TextChoices):
        MARKUP_PCT = "markup_pct", "Markup %"
        FLAT_FEE = "flat_fee", "Flat fee"
        SHIPPING = "shipping", "Shipping"
        TAX = "tax", "Tax %"
        FX_CONVERT = "fx_convert", "FX conversion"

    rule = models.ForeignKey(PricingRule, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    step_type = models.CharField(max_length=20, choices=StepType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["rule", "order"], name="unique_step_order_per_rule")
        ]

    def __str__(self) -> str:
        return f"{self.rule.name} step {self.order}: {self.step_type}={self.value}"

    def apply(self, price: Decimal) -> Decimal:
        """Applies this single step to a running price. Pure function —
        no DB access — so PricingService.compute_selling_price can be
        tested against plain Decimal math without touching the ORM.
        """
        if self.step_type == self.StepType.MARKUP_PCT:
            return price + (price * self.value / Decimal(100))
        if self.step_type == self.StepType.FLAT_FEE:
            return price + self.value
        if self.step_type == self.StepType.SHIPPING:
            return price + self.value
        if self.step_type == self.StepType.TAX:
            return price + (price * self.value / Decimal(100))
        if self.step_type == self.StepType.FX_CONVERT:
            return price * self.value
        raise ValueError(f"Unknown step_type: {self.step_type}")


class DefaultMarkup(TimeStampedModel):
    """One simple percentage markup per merchant, set from the dashboard.

    Acts as an implicit pricing rule for products that don't have their
    own PricingRule and no manual selling price: the store price (and the
    stored selling_price) become supplier_price * (1 + markup/100). A
    single value keeps the dashboard control trivially simple; merchants
    that need per-product formulas keep using PricingRule.
    """

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="default_markup",
    )
    markup_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.owner}: {self.markup_percent}% markup"
