from django.db import models
from store.models import Product
from accounts.models import Account


class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True, unique=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.cart_id


class CartItem(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Only ONE ForeignKey
    cart = models.ForeignKey(Cart, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def sub_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name}"

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"

