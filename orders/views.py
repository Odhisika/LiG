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
from .models import Order, OrderProduct
from django.contrib import messages
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO


@login_required
def place_order(request):
    current_user = request.user
    cart_items = CartItem.objects.filter(user=current_user)

    if not cart_items.exists():
        return redirect('store')

    total = sum(item.product.price * item.quantity for item in cart_items)
    tax = (total * Decimal('0.0')).quantize(Decimal('0.0'))

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            fulfillment_method = form.cleaned_data.get('fulfillment_method', 'delivery')

            # Delivery fee: within Koforidua uses the admin-set fee; outside
            # Koforidua the fee is communicated to the customer later (charged
            # 0 here). Pickup at the office carries no fee.
            delivery_fee = Decimal('0')
            delivery_zone = None
            if fulfillment_method == 'delivery':
                from pages.models import SiteSettings
                city = (form.cleaned_data.get('city') or '').strip().lower()
                if city == 'koforidua':
                    delivery_fee = SiteSettings.get_solo().delivery_fee_koforidua
                    delivery_zone = 'within_koforidua'
                else:
                    delivery_zone = 'outside_koforidua'

            grand_total = total + tax + delivery_fee

            # Create order
            order = form.save(commit=False)
            order.user = current_user
            order.order_total = grand_total
            order.tax = tax
            order.fulfillment_method = fulfillment_method
            order.delivery_zone = delivery_zone
            order.delivery_fee = delivery_fee
            if fulfillment_method == 'pickup':
                order.address_line_1 = ''
                order.address_line_2 = None
                order.country = ''
                order.state = ''
                order.city = ''
            order.ip = request.META.get('REMOTE_ADDR', '')
            order.status = 'Pending'
            order.expires_at = now() + timedelta(days=7)
            order.save()

            # Generate order number
            order.order_number = now().strftime("%Y%m%d") + str(order.id)
            order.save()

            # Move cart items to OrderProduct
            for item in cart_items:
                OrderProduct.objects.create(
                    order=order,
                    user=current_user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True
                )

            # Clear cart
            cart_items.delete()

            # Send email
            try:
                from orders.emails import send_order_placed_email
                send_order_placed_email(current_user, order)
            except Exception as e:
                print(f"Email sending failed: {e}")

            # ✅ Always redirect after successful order
            return redirect(reverse('order_complete', kwargs={'order_number': order.order_number}))

        else:
            messages.error(request, "Invalid order details. Please check your form.")
            return redirect('checkout')

    # If GET request
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

@login_required
def generate_invoice_pdf(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    
    # Security check: Ensure the order belongs to the user or user is staff
    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "You do not have permission to view this invoice.")
        return redirect('dashboard')

    order_detail = OrderProduct.objects.filter(order=order)
    subtotal = sum(item.product_price * item.quantity for item in order_detail)

    context = {
        'order': order,
        'order_detail': order_detail,
        'subtotal': subtotal,
    }
    
    # Render template to HTML string
    html_string = render_to_string('orders/invoice_pdf.html', context)
    
    # Create a file-like buffer to receive PDF data
    result = BytesIO()
    
    # Convert HTML to PDF
    pdf = pisa.pisaDocument(BytesIO(html_string.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{order_number}.pdf"'
        return response
    
    return HttpResponse("Error generating PDF", status=500)
