from rest_framework import serializers

from apps.pricing.models import PricingRule, PricingRuleStep


class PricingRuleStepInputSerializer(serializers.Serializer):
    """Used for writing steps as part of PricingRuleSerializer — order
    is implicit from list position, not supplied by the client, so
    reordering is just resubmitting the list in the new order.
    """

    step_type = serializers.ChoiceField(choices=PricingRuleStep.StepType.choices)
    value = serializers.DecimalField(max_digits=12, decimal_places=4)


class PricingRuleStepOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingRuleStep
        fields = ["order", "step_type", "value"]


class PricingRuleSerializer(serializers.ModelSerializer):
    """Steps are nested and fully replaced on every write — simpler and
    less error-prone than diffing an ordered list against existing rows,
    and pricing rules are short (a handful of steps) so this is cheap.
    """

    steps = PricingRuleStepInputSerializer(many=True, write_only=True)
    steps_display = PricingRuleStepOutputSerializer(source="steps", many=True, read_only=True)

    class Meta:
        model = PricingRule
        fields = ["id", "name", "is_active", "steps", "steps_display", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_steps(self, value: list[dict]) -> list[dict]:
        if not value:
            raise serializers.ValidationError("A pricing rule needs at least one step.")
        return value


class DefaultMarkupSerializer(serializers.Serializer):
    """The merchant's one default markup % for products without their own
    pricing rule. `affected_products` is read-only and only populated on
    write, as a hint for the UI.
    """

    markup_percent = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    affected_products = serializers.IntegerField(read_only=True, default=0)
