from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.history.models import PriceHistory


class PriceHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    price_diff = serializers.SerializerMethodField()
    stock_diff = serializers.SerializerMethodField()

    class Meta:
        model = PriceHistory
        fields = [
            "id",
            "product",
            "product_name",
            "old_price",
            "new_price",
            "price_diff",
            "old_stock",
            "new_stock",
            "stock_diff",
            "price_changed",
            "stock_changed",
            "source",
            "reason",
            "created_at",
        ]
        # History is immutable — this API never accepts writes, only reads.
        read_only_fields = fields

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_price_diff(self, obj: PriceHistory) -> Decimal:
        return obj.new_price - obj.old_price

    @extend_schema_field(serializers.IntegerField(allow_null=True))
    def get_stock_diff(self, obj: PriceHistory) -> int | None:
        if obj.old_stock is None or obj.new_stock is None:
            return None
        return obj.new_stock - obj.old_stock
