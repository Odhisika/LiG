from rest_framework import serializers


class SupplierActivitySerializer(serializers.Serializer):
    supplier_id = serializers.UUIDField()
    supplier_name = serializers.CharField()
    change_count = serializers.IntegerField()


class ProductVolatilitySerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    change_count = serializers.IntegerField()


class PriceSwingSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    old_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    new_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    diff = serializers.DecimalField(max_digits=12, decimal_places=2)
    created_at = serializers.DateTimeField()


class ProfitImpactSerializer(serializers.Serializer):
    total_potential_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_margin = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    products_with_pricing = serializers.IntegerField()


class AnalyticsSummarySerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    total_changes_in_period = serializers.IntegerField()
    average_daily_changes = serializers.DecimalField(max_digits=10, decimal_places=2)
    most_active_suppliers = SupplierActivitySerializer(many=True)
    most_volatile_products = ProductVolatilitySerializer(many=True)
    largest_price_increases = PriceSwingSerializer(many=True)
    largest_price_decreases = PriceSwingSerializer(many=True)
    profit_impact = ProfitImpactSerializer()
