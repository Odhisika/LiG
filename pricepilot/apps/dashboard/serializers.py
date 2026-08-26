from rest_framework import serializers


class ProductsByStatusSerializer(serializers.Serializer):
    active = serializers.IntegerField()
    paused = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    scrape_failed = serializers.IntegerField()
    archived = serializers.IntegerField()


class ProductsByCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()


class ActivityEventSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", default=None, read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", default=None, read_only=True)

    class Meta:
        from apps.dashboard.models import ActivityEvent

        model = ActivityEvent
        fields = [
            "id",
            "event_type",
            "product",
            "product_name",
            "supplier",
            "supplier_name",
            "payload",
            "created_at",
        ]


class DashboardSummarySerializer(serializers.Serializer):
    products_monitored = serializers.IntegerField()
    suppliers_count = serializers.IntegerField()
    products_by_status = ProductsByStatusSerializer()
    products_by_category = ProductsByCategorySerializer(many=True)
    average_profit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    default_markup = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )
    products_changed_today = serializers.IntegerField()
    stock_changes_today = serializers.IntegerField()
    failed_scrapes_today = serializers.IntegerField()
    todays_checks = serializers.IntegerField()
    recent_activity = serializers.ListField(child=serializers.DictField())
