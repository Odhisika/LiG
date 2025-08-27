from .models import Cart, CartItem
from store.models import Product
from django.core.exceptions import ObjectDoesNotExist


class CartManager:
    def __init__(self, request):
        self.request = request
        self.user = request.user
        self.session = request.session
        self.cart_id = self._get_cart_id()

    def _get_cart_id(self):
        """Return or create a session cart_id for guests"""
        cart_id = self.session.session_key
        if not cart_id:
            cart_id = self.session.create()
        return cart_id

    def get_cart(self):
        """Return the Cart object (for guest users only)"""
        cart, created = Cart.objects.get_or_create(cart_id=self.cart_id)
        return cart

    def add(self, product, quantity=1):
        """Add product to cart or update quantity"""
        if self.user.is_authenticated:
            cart_item, created = CartItem.objects.get_or_create(
                product=product,
                user=self.user,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
            cart_item.save()
        else:
            cart = self.get_cart()
            cart_item, created = CartItem.objects.get_or_create(
                product=product,
                cart=cart,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
            cart_item.save()

    def remove(self, product, cart_item_id=None):
        """Remove one quantity of the product or delete item"""
        try:
            if self.user.is_authenticated:
                cart_item = CartItem.objects.get(product=product, user=self.user, id=cart_item_id)
            else:
                cart = self.get_cart()
                cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)

            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
        except CartItem.DoesNotExist:
            pass

    def remove_item(self, product, cart_item_id=None):
        """Completely remove product from cart"""
        try:
            if self.user.is_authenticated:
                CartItem.objects.get(product=product, user=self.user, id=cart_item_id).delete()
            else:
                cart = self.get_cart()
                CartItem.objects.get(product=product, cart=cart, id=cart_item_id).delete()
        except CartItem.DoesNotExist:
            pass

    def clear(self):
        """Clear all items from cart"""
        if self.user.is_authenticated:
            CartItem.objects.filter(user=self.user).delete()
        else:
            try:
                cart = self.get_cart()
                CartItem.objects.filter(cart=cart).delete()
            except ObjectDoesNotExist:
                pass

    def get_items(self):
        """Get all active cart items"""
        if self.user.is_authenticated:
            return CartItem.objects.filter(user=self.user, is_active=True)
        else:
            try:
                cart = self.get_cart()
                return CartItem.objects.filter(cart=cart, is_active=True)
            except ObjectDoesNotExist:
                return []

    def get_totals(self):
        """Calculate totals"""
        total, quantity = 0, 0
        cart_items = self.get_items()
        for item in cart_items:
            total += item.product.price * item.quantity
            quantity += item.quantity
        tax = (0 * total) / 100
        grand_total = total + tax
        return {
            'total': total,
            'quantity': quantity,
            'tax': tax,
            'grand_total': grand_total,
        }
