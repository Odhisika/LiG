from django.test import TestCase

# Create your tests here.


from django.db import models
from accounts.models import Account
from store.models import Product
from datetime import timedelta
from django.utils.timezone import now
from decimal import Decimal
import datetime
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.shortcuts import redirect
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.conf import settings
import requests
from payment.models import Payment



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
    paid = models.BooleanField(default=False)
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
    

class PaymentProof(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    proof_image = models.ImageField(upload_to='payment_proofs/')
    note = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reviewed = models.BooleanField(default=False)

    def __str__(self):
        return f'Proof for Order #{self.order.order_number}'

class OrderManager(models.Manager):
    def get_user_statistics(self, user):
        """Get order statistics for a specific user"""
        orders = self.filter(user=user)
        total_spent = orders.aggregate(total=Sum('order_total'))['total'] or 0
        total_orders = orders.count()
        
        current_year = timezone.now().year
        orders_this_year = orders.filter(created_at__year=current_year).count()
        
        return {
            'total_orders': total_orders,
            'total_spent': total_spent,
            'orders_this_year': orders_this_year,
        }
# views.py


from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.timezone import now,timedelta
from django.urls import reverse
from decimal import Decimal

from cart.models import CartItem
from .forms import OrderForm
from .models import Order, OrderProduct, PaymentProof
from django.contrib import messages


@login_required
def place_order(request):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)

    if not cart_items.exists():
        return redirect('store')

    total = sum(item.product.price * item.quantity for item in cart_items)
    tax = (total * Decimal('0.0')).quantize(Decimal('0.0'))
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = form.save(commit=False)
            data.user = current_user
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR', '')
            data.status = 'Pending Payment'
            data.expires_at = now() + timedelta(days=7)
            data.save()

            # Generate order number
            data.save()
            data.refresh_from_db()  # Ensures ID is present
            data.order_number = now().strftime("%Y%m%d") + str(data.id)
            data.save()

            # Move cart items to OrderProduct
            for item in cart_items:
                order_product = OrderProduct.objects.create(
                    order=data,
                    user=current_user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True
                )
                order_product.save()

            # Clear cart
            cart_items.delete()

            # Send confirmation email with payment instructions
            mail_subject = 'Order Placed - Make Payment'
            message = render_to_string('orders/payment_instructions_email.html', {
                'user': request.user,
                'order': data,
            })
            try:
                send_email = EmailMessage(mail_subject, message, to=[request.user.email])
                send_email.send()
            except Exception as e:
                print(f"Email sending failed: {e}")

            return redirect(reverse('order_complete', kwargs={'order_number': data.order_number}))

    return redirect('checkout')


@login_required
def order_complete(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, is_ordered=False)

    ordered_products = OrderProduct.objects.filter(order=order)
    subtotal = sum(item.product_price * item.quantity for item in ordered_products)

    # Send invoice email
    send_order_invoice(request.user, order, ordered_products, subtotal)

    return render(request, 'orders/order_complete.html', {
        'order': order,
        'ordered_products': ordered_products,
        'order_number': order.order_number,
        'subtotal': subtotal,
    })


def submit_proof(request, order_number):
    if request.method == 'POST':
        order = get_object_or_404(Order, order_number=order_number)
        user = request.user
        proof_file = request.FILES.get('proof')
        note = request.POST.get('note')

        if proof_file:
            payment_proof = PaymentProof.objects.create(
                order=order,
                user=user,
                proof_image=proof_file,
                note=note
            )
            order.status = 'New'
            order.save()

            # Redirect to confirmation step
            return redirect('confirm_payment', proof_id=payment_proof.id)

    return redirect('home')



def confirm_payment(request, proof_id):
    proof = get_object_or_404(PaymentProof, id=proof_id, user=request.user)

    if request.method == 'POST':
        messages.success(request, "Thank you! We'll review your order and process it as soon as possible.")
        return redirect('order_detail', order_id=proof.order.order_number)

    return render(request, 'orders/confirm_payment.html', {'proof': proof})



def send_order_invoice(user, order, order_detail, subtotal):
    subject = "Order Invoice - Thank You for Your Purchase"
    from_email = "francisganyo64@gmail.com "  
    recipient_list = [user.email]

   
    html_content = render_to_string(
        "orders/invoice_template.html",
        {"user": user, "order": order, "order_detail": order_detail, "subtotal": subtotal},
    )

    # Strip HTML tags for a plain text version
    text_content = strip_tags(html_content)

    # Send the email with both HTML and plain text versions
    email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
    email.attach_alternative(html_content, "text/html")
    email.send()


from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('order_complete/<str:order_number>/', views.order_complete, name='order_complete'),
    path('submit-proof/<str:order_number>/', views.submit_proof, name='submit_proof'),
    path('confirm-payment/<int:proof_id>/', views.confirm_payment, name='confirm_payment'),
    

]
