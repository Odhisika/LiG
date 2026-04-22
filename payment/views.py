# payment/views.py - Enhanced debugging version with Hubtel support
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from django.conf import settings
from django.db import models
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


def initialize_payment(request, order_id, gateway='paystack'):
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
        callback_url = request.build_absolute_uri(reverse('verify_payment'))
        
        description = f"Order {order.order_number} - LiG Store"
        customer_name = f"{order.first_name} {order.last_name}".strip() or "Customer"
        
        success, result = hubtel.initialize_transaction(
            amount=float(payment.amount),
            description=description,
            customer_email=payment.email,
            customer_name=customer_name,
            reference=payment.ref,
            callback_url=callback_url,
            mobile_money=True
        )
        
        if success:
            payment.hubtel_token = result.get('token')
            payment.hubtel_checkout_url = result.get('checkout_url')
            payment.authorization_url = result.get('checkout_url')
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
        messages.error(request, "Hubtel authentication error. Please try Paystack instead.")
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
        request.GET.get("TransactionId")
    )
    
    if not reference:
        messages.error(request, "No payment reference provided.")
        return redirect('cart')
    
    try:
        # Find payment by reference
        payment = Payment.objects.filter(
            models.Q(ref=reference) | 
            models.Q(paystack_reference=reference) |
            models.Q(hubtel_token=reference)
        ).first()
        
        if not payment:
            messages.error(request, "Payment record not found.")
            return redirect('cart')
        
        # Verify the payment
        try:
            verified = payment.verify_payment(transaction_id)
        except Exception as verify_error:
            print(f"Error in payment.verify_payment(): {str(verify_error)}")
            messages.error(request, "Payment verification failed.")
            return redirect('cart')
        
        if verified and payment.is_successful():
            # Clear cart
            if request.user.is_authenticated:
                CartItem.objects.filter(user=request.user, is_active=True).delete()
            else:
                try:
                    cart = Cart.objects.get(cart_id=_cart_id(request))
                    CartItem.objects.filter(cart=cart, is_active=True).delete()
                    cart.delete()
                except Cart.DoesNotExist:
                    pass
            
            context = {
                "payment": payment,
                "order": payment.order,
                "success": True
            }
            
            gateway_name = "Hubtel" if payment.gateway == 'hubtel' else "Paystack"
            messages.success(request, f"Payment successful via {gateway_name}! Order {payment.order.order_number} has been confirmed.")
            return render(request, "payment/payment_success.html", context)
        else:
            messages.error(request, "Payment verification failed. Please contact support if you were charged.")
            context = {
                "payment": payment,
                "order": payment.order,
                "success": False
            }
            return render(request, "payment/payment_failed.html", context)
            
    except Exception as e:
        logger.error(f"Error verifying payment {reference}: {str(e)}")
        messages.error(request, "An error occurred while verifying your payment.")
        return redirect('cart')


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
    """Check payment status (AJAX endpoint)"""
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Verify payment if still pending
        if payment.status == 'pending':
            payment.verify_payment()
        
        return JsonResponse({
            'status': payment.status,
            'verified': payment.verified,
            'success': payment.is_successful()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
    """Handle Hubtel webhook notifications"""
    try:
        data = json.loads(request.body)
        logger.info(f"Hubtel webhook received: {data}")
        
        # Hubtel sends transaction status updates
        status = data.get('status') or data.get('Status')
        reference = data.get('clientReference') or data.get('ClientReference') or data.get('reference')
        transaction_id = data.get('transactionId') or data.get('TransactionId')
        
        if reference and status:
            payment = Payment.objects.filter(ref=reference).first()
            
            if payment:
                if status.lower() in ['completed', 'success', 'approved', 'successfull']:
                    payment.verify_payment(transaction_id)
                elif status.lower() in ['failed', 'cancelled']:
                    payment.status = 'failed'
                    payment.save()
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Hubtel webhook error: {str(e)}")
        return HttpResponse("Error", status=500)