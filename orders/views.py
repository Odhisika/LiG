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
