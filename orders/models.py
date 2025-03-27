from django.db import models
from accounts.models import Account
from store.models import Product
from datetime import timedelta
from django.utils.timezone import now
from decimal import Decimal
import datetime

class Order(models.Model):
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Pending Payment', 'Pending Payment'),
        ('Expired', 'Expired'),
        ('Accepted', 'Accepted'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    order_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    country = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    order_note = models.TextField(blank=True, null=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending Payment')
    ip = models.GenericIPAddressField(blank=True, null=True)
    is_ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def default_expiry():
       return datetime.datetime.now() + datetime.timedelta(days=7)
    expires_at = models.DateTimeField(default=default_expiry)

    def order_count(cls):
        return cls.objects.count()


    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def full_address(self):
        return f"{self.address_line_1}, {self.address_line_2 or ''}, {self.city}, {self.state}, {self.country}".strip(', ')

    def __str__(self):
        return f"Order {self.order_number} - {self.status}"


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_products')
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    ordered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.product_name} (x{self.quantity})"
