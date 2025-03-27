from django.utils.timezone import now
from .models import Order

def delete_expired_orders():
    expired_orders = Order.objects.filter(status='Pending Payment', expires_at__lte=now())
    for order in expired_orders:
        order.delete()
