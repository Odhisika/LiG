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


class DashboardSummarySerializer(serializers.Serializer):
    """Shape of GET /api/dashboard/summary/.

    Fields marked "Phase 2" are real fields with honest zero/empty
    values today — they depend on History/ScrapeLog models that don't
    exist yet. They're included now so the API contract doesn't change
    shape later; only the values start populating once Phase 2 lands.
    """

    products_monitored = serializers.IntegerField()
    suppliers_count = serializers.IntegerField()
    products_by_status = ProductsByStatusSerializer()
    products_by_category = ProductsByCategorySerializer(many=True)
    average_profit = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    default_markup = serializers.DecimalField(
        max_digits=5, decimal_places=2, allow_null=True
    )

    # --- Phase 2 (History / ScrapeLog) — placeholders until then ---
    products_changed_today = serializers.IntegerField()
    stock_changes_today = serializers.IntegerField()
    failed_scrapes_today = serializers.IntegerField()
    todays_checks = serializers.IntegerField()
    recent_activity = serializers.ListField(child=serializers.DictField())
