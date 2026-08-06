from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _send_email(subject, html_template, context, to_email):
    html_content = render_to_string(html_template, context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(subject, text_content, to=[to_email])
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_order_placed_email(user, order):
    """Notify the customer that their order has been placed (awaiting payment)."""
    _send_email(
        subject=f"Order Placed - #{order.order_number} - Make Payment",
        html_template="orders/payment_instructions_email.html",
        context={"user": user, "order": order},
        to_email=user.email,
    )


def send_payment_success_email(payment):
    """Notify the customer that their payment was confirmed."""
    order = payment.order
    user = payment.user
    _send_email(
        subject=f"Payment Confirmed - Order #{order.order_number}",
        html_template="orders/payment_success_email.html",
        context={"user": user, "order": order, "payment": payment},
        to_email=payment.email or user.email,
    )


def send_order_status_email(order, old_status, new_status):
    """Notify the customer when the fulfillment status of their order changes."""
    user = order.user
    _send_email(
        subject=f"Order #{order.order_number} is now {new_status}",
        html_template="orders/order_status_email.html",
        context={
            "user": user,
            "order": order,
            "old_status": old_status,
            "new_status": new_status,
        },
        to_email=order.email or user.email,
    )
