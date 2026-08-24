from django.contrib import admin

from apps.pricing.models import PricingRule, PricingRuleStep


class PricingRuleStepInline(admin.TabularInline):
    model = PricingRuleStep
    extra = 1
    ordering = ["order"]


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "is_active", "created_at"]
    search_fields = ["name", "owner__email"]
    inlines = [PricingRuleStepInline]
