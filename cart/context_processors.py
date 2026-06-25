from .models import Cart, CartItem
from .views import _cart_id


def counter(request):
    cart_count = 0
    cart_product_ids = set()
    if 'admin' in request.path:
        return {}
    else:
        cart = Cart.objects.filter(cart_id=_cart_id(request))
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user)
        else:
            cart_items = CartItem.objects.filter(cart=cart[:1]) if cart.exists() else CartItem.objects.none()
        for cart_item in cart_items:
            cart_count += cart_item.quantity
            cart_product_ids.add(cart_item.product_id)
    return dict(cart_count=cart_count, cart_product_ids=cart_product_ids)



