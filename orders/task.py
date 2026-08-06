from django.utils.timezone import now
from .models import Order

def delete_expired_orders():
    expired_orders = Order.objects.filter(paid=False, expires_at__lte=now())
    for order in expired_orders:
        order.delete()
