# payment/views.py - Enhanced debugging version with Hubtel support
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, QueryDict
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import json
import logging
import traceback
from cart.views import _cart_id
from .models import Payment
from orders.models import Order
from cart.models import Cart
from .paystack import Paystack
from .hubtel import Hubtel, HubtelException
from cart.models import Cart, CartItem

logger = logging.getLogger(__name__)

HUBTEL_STATUS_CHECK_DELAY = timedelta(minutes=5)
HUBTEL_STATUS_CHECK_CACHE_TTL = int(HUBTEL_STATUS_CHECK_DELAY.total_seconds())
LOCAL_PAYMENT_STATUS_POLL_SECONDS = 10


def _build_callback_url(request, route_name):
    """
    Build an external callback URL.

    Keep localhost on HTTP for Django's dev server. For non-local hosts,
    prefer HTTPS so Hubtel callbacks do not get downgraded through redirects.
    """
    url = request.build_absolute_uri(reverse(route_name))
    host = request.get_host().split(':', 1)[0].lower()
    is_localhost = host in {'localhost', '127.0.0.1', '0.0.0.0'}

    if is_localhost or request.is_secure():
        return url

    return url.replace('http://', 'https://', 1)


def _hubtel_status_check_cache_key(payment_id):
    return f"hubtel-status-check:{payment_id}"


def _get_hubtel_status_check_wait_seconds(payment):
    if payment.gateway != 'hubtel' or not payment.created_at:
        return 0

    initial_wait = payment.created_at + HUBTEL_STATUS_CHECK_DELAY
    remaining = int((initial_wait - timezone.now()).total_seconds())
    if remaining > 0:
        return remaining

    last_status_check_at = cache.get(_hubtel_status_check_cache_key(payment.id))
    if not last_status_check_at:
        return 0

    retry_at = last_status_check_at + HUBTEL_STATUS_CHECK_DELAY
    retry_remaining = int((retry_at - timezone.now()).total_seconds())
    return max(0, retry_remaining)


def _record_hubtel_status_check(payment):
    cache.set(
        _hubtel_status_check_cache_key(payment.id),
        timezone.now(),
        timeout=HUBTEL_STATUS_CHECK_CACHE_TTL,
    )


def _render_hubtel_processing(request, payment):
    return render(
        request,
        "payment/payment_processing.html",
        {
            "payment": payment,
            "order": payment.order,
            "status_check_wait_seconds": _get_hubtel_status_check_wait_seconds(payment),
            "status_poll_seconds": LOCAL_PAYMENT_STATUS_POLL_SECONDS,
        },
    )


def initialize_payment(request, order_id, gateway='hubtel'):
    """Initialize payment for an order with selected gateway"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        # Check if user owns this order
        if request.user.is_authenticated and order.user != request.user:
            messages.error(request, "You don't have permission to access this order.")
            return redirect('cart')
        
        # Check if order is already paid
        existing_payment = Payment.get_successful_payment_for_order(order)
        if existing_payment:
            messages.info(request, "This order has already been paid for.")
            return redirect('order_complete', order_number=order.order_number)
        
        # Validate gateway
        if gateway not in ['paystack', 'hubtel']:
            messages.error(request, "Invalid payment gateway selected.")
            return redirect('cart')
        
        # Delete any existing pending payments for this order
        Payment.objects.filter(order=order, status='pending').delete()
        
        # Create new payment record with selected gateway
        payment = Payment.objects.create(
            user=order.user,
            order=order,
            amount=order.order_total,
            email=order.email,
            status='pending',
            gateway=gateway
        )
        
        if gateway == 'hubtel':
            return _initialize_hubtel_payment(request, order, payment)
        else:
            return _initialize_paystack_payment(request, order, payment)
            
    except Exception as e:
        logger.error(f"Error initializing payment for order {order_id}: {str(e)}")
        print(f"Full traceback in initialize_payment: {traceback.format_exc()}")
        messages.error(request, "An error occurred while processing your payment. Please try again.")
        return redirect('cart')


def _initialize_paystack_payment(request, order, payment):
    """Initialize Paystack payment"""
    try:
        paystack = Paystack()
        callback_url = request.build_absolute_uri(reverse('verify_payment'))
        
        metadata = {
            "order_id": order.id,
            "order_number": order.order_number,
            "payment_id": payment.id
        }
        
        success, result = paystack.initialize_transaction(
            email=payment.email,
            amount=payment.amount_in_pesewas(),
            reference=payment.ref,
            callback_url=callback_url,
            metadata=metadata
        )
        
        if success:
            payment.paystack_reference = result.get('reference', payment.ref)
            payment.authorization_url = result.get('authorization_url')
            payment.access_code = result.get('access_code')
            payment.save()
            
            return redirect(payment.authorization_url)
        else:
            messages.error(
                request, 
                f"Paystack payment failed: {result.get('message', 'Unknown error')}"
            )
            payment.status = 'failed'
            payment.save()
            return redirect('order_complete', order_number=order.order_number)
            
    except Exception as e:
        logger.error(f"Paystack initialization error: {str(e)}")
        messages.error(request, "Payment gateway error. Please try again.")
        payment.status = 'failed'
        payment.save()
        return redirect('cart')


def _initialize_hubtel_payment(request, order, payment):
    """Initialize Hubtel payment"""
    try:
        hubtel = Hubtel()

        # returnUrl  → user is redirected here after completing payment (GET)
        # callbackUrl → Hubtel POSTs the final result here server-to-server (POST)
        #
        # IMPORTANT: Hubtel does NOT always append query params to returnUrl.
        # We bake our own reference into the URL so it's always present.
        # Keep localhost on HTTP because Django's dev server does not support HTTPS.
        # For non-local hosts, prefer HTTPS to avoid callback redirects.
        base_verify_url  = _build_callback_url(request, 'verify_payment')
        return_url       = f"{base_verify_url}?clientReference={payment.ref}"
        cancellation_url = f"{base_verify_url}?clientReference={payment.ref}&cancelled=1"
        webhook_url      = _build_callback_url(request, 'hubtel_webhook')

        description   = f"Order {order.order_number} - LiG Store"
        customer_name = f"{order.first_name} {order.last_name}".strip() or "Customer"

        success, result = hubtel.initialize_transaction(
            amount=float(payment.amount),
            description=description,
            customer_email=payment.email,
            customer_name=customer_name,
            reference=payment.ref,
            callback_url=webhook_url,       # server-to-server POST
            return_url=return_url,          # browser redirect after payment
            cancellation_url=cancellation_url,
        )

        if success:
            payment.hubtel_token        = result.get('token')
            payment.hubtel_checkout_url = result.get('checkout_url')
            payment.authorization_url   = result.get('checkout_url')
            payment.save()
            return redirect(payment.authorization_url)
        else:
            messages.error(
                request,
                f"Hubtel payment failed: {result.get('message', 'Unknown error')}"
            )
            payment.status = 'failed'
            payment.save()
            return redirect('order_complete', order_number=order.order_number)

    except HubtelException as e:
        logger.error(f"Hubtel initialization error: {str(e)}")
        messages.error(request, "Hubtel authentication error. Please try again.")
        payment.status = 'failed'
        payment.save()
        return redirect('cart')
    except Exception as e:
        logger.error(f"Hubtel initialization error: {str(e)}")
        messages.error(request, "Payment gateway error. Please try again.")
        payment.status = 'failed'
        payment.save()
        return redirect('cart')


def verify_payment(request):
    reference = (
        request.GET.get("reference") or
        request.GET.get("clientReference") or
        request.GET.get("ClientReference")
    )
    transaction_id = (
        request.GET.get("transactionId") or
        request.GET.get("TransactionId") or
        request.GET.get("checkoutId") or
        request.GET.get("CheckoutId") or
        request.GET.get("checkoutid") or
        request.GET.get("salesId") or
        request.GET.get("SalesId")
    )
    cancelled = request.GET.get("cancelled")

    if not reference:
        messages.error(request, "No payment reference provided.")
        return redirect('cart')

    try:
        payment = Payment.objects.filter(
            models.Q(ref=reference) |
            models.Q(paystack_reference=reference) |
            models.Q(hubtel_token=reference)
        ).first()

        if not payment:
            messages.error(request, "Payment record not found.")
            return redirect('cart')

        # Customer cancelled on Hubtel's page
        if cancelled:
            messages.warning(request, "Payment was cancelled. You can try again.")
            return redirect('order_complete', order_number=payment.order.order_number)


        # Already verified by webhook before browser landed here
        if payment.is_successful():
            _clear_cart(request)
            gateway_name = "Hubtel" if payment.gateway == 'hubtel' else "Paystack"
            messages.success(
                request,
                f"Payment successful via {gateway_name}! "
                f"Order {payment.order.order_number} has been confirmed."
            )
            return render(request, "payment/payment_success.html",
                          {"payment": payment, "order": payment.order, "success": True})

        if payment.gateway == 'hubtel':
            wait_seconds = _get_hubtel_status_check_wait_seconds(payment)
            if wait_seconds > 0:
                logger.info(
                    f"Hubtel status check for {reference} deferred for {wait_seconds}s "
                    f"to respect the 5-minute verification window."
                )
                return _render_hubtel_processing(request, payment)

        # Hubtel may omit the transaction/check-out id on return.
        # Fall back to the stored Hubtel checkout id when we have one.
        if (
            payment.gateway == 'hubtel' and
            not transaction_id and
            payment.hubtel_token and
            not payment.hubtel_token.startswith('PAY_')
        ):
            transaction_id = payment.hubtel_token

        # Hubtel redirect with no TransactionId → stay on processing page and
        # let the webhook or the delayed merchant status check confirm payment.
        if payment.gateway == 'hubtel' and not transaction_id:
            logger.info(
                f"Hubtel returnUrl for {reference} has no TransactionId — waiting on webhook or delayed status check."
            )
            return _render_hubtel_processing(request, payment)

        # Normal verification (Paystack, or Hubtel with a TransactionId)
        try:
            if payment.gateway == 'hubtel':
                _record_hubtel_status_check(payment)
            verified = payment.verify_payment(transaction_id)
        except Exception as verify_error:
            logger.error(f"Error in payment.verify_payment(): {str(verify_error)}")
            if payment.gateway == 'hubtel':
                return _render_hubtel_processing(request, payment)
            messages.error(request, "Payment verification failed. Please contact support.")
            return redirect('cart')

        if verified and payment.is_successful():
            _clear_cart(request)
            gateway_name = "Hubtel" if payment.gateway == 'hubtel' else "Paystack"
            messages.success(
                request,
                f"Payment successful via {gateway_name}! "
                f"Order {payment.order.order_number} has been confirmed."
            )
            return render(request, "payment/payment_success.html",
                          {"payment": payment, "order": payment.order, "success": True})

        # Not confirmed yet (pending) — redirect to home
        if payment.status == 'pending' and payment.gateway == 'hubtel':
            return _render_hubtel_processing(request, payment)

        # Explicitly failed
        messages.error(request, "Payment was not successful. Please contact support if you were charged.")
        return render(request, "payment/payment_failed.html",
                      {"payment": payment, "order": payment.order, "success": False})

    except Exception as e:
        logger.error(f"Error verifying payment {reference}: {str(e)}")
        messages.error(request, "An error occurred while verifying your payment.")
        return redirect('cart')


def _clear_cart(request):
    """Remove all cart items after a successful payment."""
    if request.user.is_authenticated:
        CartItem.objects.filter(user=request.user, is_active=True).delete()
    else:
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            CartItem.objects.filter(cart=cart, is_active=True).delete()
            cart.delete()
        except Cart.DoesNotExist:
            pass


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """Handle Paystack webhook notifications"""
    try:
        payload = request.body
        signature = request.headers.get('x-paystack-signature')
        
        if not signature:
            return HttpResponse("No signature", status=400)
        
        # Verify webhook signature (implement based on Paystack docs)
        # This is important for security
        
        data = json.loads(payload)
        event = data.get('event')
        
        if event == 'charge.success':
            reference = data.get('data', {}).get('reference')
            if reference:
                try:
                    payment = Payment.objects.filter(
                        models.Q(ref=reference) | models.Q(paystack_reference=reference)
                    ).first()
                    
                    if payment:
                        payment.verify_payment()
                        
                except Exception as e:
                    logger.error(f"Error processing webhook for {reference}: {str(e)}")
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return HttpResponse("Error", status=500)


def payment_status(request, payment_id):
    """AJAX polling endpoint — check payment status and try to verify if pending."""
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        next_status_check_in = 0

        if payment.status == 'pending' and payment.gateway == 'hubtel':
            next_status_check_in = _get_hubtel_status_check_wait_seconds(payment)

            if next_status_check_in == 0:
                txn_id = payment.hubtel_token or None
                _record_hubtel_status_check(payment)

                # Only call the API if we have a real Hubtel ID (not our own PAY_xxx ref)
                if txn_id and not txn_id.startswith('PAY_'):
                    payment.verify_payment(txn_id)
                else:
                    # Try using clientReference-only lookup
                    payment.verify_payment(None)

                payment.refresh_from_db()
                next_status_check_in = _get_hubtel_status_check_wait_seconds(payment)

        return JsonResponse({
            'status': payment.status,
            'verified': payment.verified,
            'success': payment.is_successful(),
            'ref': payment.ref,
            'next_status_check_in': next_status_check_in,
        })

    except Exception as e:
        logger.error(f"payment_status error: {str(e)}")
        return JsonResponse({'error': str(e), 'status': 'pending', 'verified': False, 'success': False})


def payment_detail(request, payment_id):
    """Display payment details"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Check permissions
    if request.user.is_authenticated and payment.user != request.user:
        messages.error(request, "You don't have permission to view this payment.")
        return redirect('cart')
    
    context = {
        'payment': payment,
        'order': payment.order
    }
    
    return render(request, 'payment/payment_detail.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def hubtel_webhook(request):
    """
    Hubtel server-to-server callback (callbackUrl).
    Hubtel POSTs the payment result here after the customer completes payment.
    This is the authoritative source — verify and mark payment immediately.
    """
    try:
        raw_body = request.body.decode('utf-8')
        logger.info(f"Hubtel webhook RAW body: {raw_body[:1000]}")

        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            data = json.loads(raw_body)
        else:
            data = QueryDict(raw_body).dict()

        logger.info(f"Hubtel webhook parsed: {data}")

        # Hubtel may nest data inside a 'Data' or 'data' key
        payload = data.get('Data') or data.get('data') or data

        # Extract key fields — Hubtel uses various casing
        status = (
            payload.get('Status') or payload.get('status') or
            payload.get('TransactionStatus') or payload.get('transactionStatus') or
            payload.get('ResponseCode') or payload.get('ResponseDescription') or ''
        ).lower()

        reference = (
            payload.get('ClientReference') or payload.get('clientReference') or
            payload.get('ClientRef') or payload.get('reference') or ''
        )

        transaction_id = (
            payload.get('TransactionId') or payload.get('transactionId') or
            payload.get('CheckoutId') or payload.get('checkoutId') or
            payload.get('PosTransactionId') or ''
        )

        logger.info(
            f"Hubtel webhook → status='{status}' ref='{reference}' txn_id='{transaction_id}'"
        )

        if not reference:
            logger.warning("Hubtel webhook: no clientReference found in payload.")
            return HttpResponse("OK", status=200)  # still return 200 so Hubtel doesn't retry

        payment = Payment.objects.filter(
            models.Q(ref=reference) |
            models.Q(hubtel_token=reference)
        ).first()

        if not payment:
            logger.warning(f"Hubtel webhook: no payment found for ref='{reference}'")
            return HttpResponse("OK", status=200)

        if payment.verified:
            logger.info(f"Hubtel webhook: payment {reference} already verified — skipping.")
            return HttpResponse("OK", status=200)

        if status in ('success', 'successfull', 'completed', 'approved', '0000'):
            logger.info(f"Hubtel webhook: marking {reference} successful from callback payload.")
            payment.mark_hubtel_success({
                'transaction_id': transaction_id or None,
                'paymentMethod': payload.get('PaymentMethod') or payload.get('paymentMethod'),
                'currency': payload.get('Currency') or payload.get('currency'),
                'TransactionDate': (
                    payload.get('TransactionDate') or
                    payload.get('DatePaid') or
                    payload.get('TransactionDateTime')
                ),
                'last4': payload.get('Last4') or payload.get('last4'),
            })
        elif status in ('failed', 'cancelled', 'rejected'):
            payment.status = 'failed'
            payment.save()
            logger.info(f"Hubtel webhook: payment {reference} marked as failed.")

        return HttpResponse("OK", status=200)

    except json.JSONDecodeError:
        logger.error(f"Hubtel webhook: invalid JSON body — {request.body[:200]}")
        return HttpResponse("OK", status=200)  # return 200 anyway
    except Exception as e:
        logger.error(f"Hubtel webhook error: {str(e)}")
        return HttpResponse("OK", status=200)
