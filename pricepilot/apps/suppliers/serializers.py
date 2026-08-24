from rest_framework import serializers

from apps.suppliers.models import Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "website",
            "catalog_url",
            "country",
            "currency",
            "default_scraper",
            "rate_limit_per_minute",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_rate_limit_per_minute(self, value: int) -> int:
        if value < 1:
            raise serializers.ValidationError("rate_limit_per_minute must be at least 1.")
        return value
