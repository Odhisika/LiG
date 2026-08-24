from rest_framework import serializers

from apps.products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    # What the store actually charges for this product right now: the
    # manual selling_price, else the owner's default markup applied to the
    # supplier price, else the raw supplier price. Mirrors the store sync.
    effective_selling_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "name",
            "supplier_url",
            "sku",
            "supplier_price",
            "selling_price",
            "effective_selling_price",
            "pricing_rule",
            "currency",
            "status",
            "stock",
            "images",
            "description",
            "category",
            "check_frequency_minutes",
            "last_checked_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_checked_at", "created_at", "updated_at"]

    def get_effective_selling_price(self, obj) -> str | None:
        from apps.pricing.services import DefaultMarkupService, PricingService

        if isinstance(self.context, dict) and "markup_percent" in self.context:
            markup = self.context["markup_percent"]
        else:
            markup = DefaultMarkupService.get_markup_percent(obj.owner)

        effective = PricingService.effective_selling_price(
            obj.supplier_price,
            selling_price=obj.selling_price,
            markup_percent=markup,
        )
        return str(effective) if effective is not None else None

    def validate_check_frequency_minutes(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("check_frequency_minutes must be at least 1.")
        return value

    def validate_images(self, value) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("images must be a list of URLs.")
        return value
