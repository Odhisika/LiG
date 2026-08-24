from rest_framework import serializers

from apps.discovery.models import DiscoveredProduct


class DiscoveredProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = DiscoveredProduct
        fields = [
            "id",
            "supplier",
            "supplier_name",
            "url",
            "title",
            "price",
            "currency",
            "image",
            "status",
            "imported_product",
            "created_at",
        ]
        read_only_fields = fields


class ImportDiscoveryInputSerializer(serializers.Serializer):
    """Optional overrides for the one-click import — everything here is
    optional because DiscoveredProduct's preview data is usually enough
    on its own; this exists for the cases where it isn't (no price
    found automatically, wrong currency guessed, etc.).
    """

    name = serializers.CharField(required=False)
    supplier_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    currency = serializers.CharField(required=False)
    sku = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    check_frequency_minutes = serializers.IntegerField(required=False, min_value=1)
    pricing_rule = serializers.UUIDField(required=False, allow_null=True)
