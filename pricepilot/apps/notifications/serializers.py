from rest_framework import serializers

from apps.notifications.models import NotificationEvent


class NotificationEventSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True, default=None)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)

    class Meta:
        model = NotificationEvent
        fields = [
            "id",
            "event_type",
            "product",
            "product_name",
            "supplier",
            "supplier_name",
            "payload",
            "sent",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
