# payment/views.py - Enhanced debugging version
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
from cart.models import Cart, CartItem

logger = logging.getLogger(__name__)


def initialize_payment(request, order_id):
    """Initialize payment for an order"""
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
        
        # Check for pending payment and use it if exists
        pending_payment = Payment.objects.filter(
            order=order, 
            status='pending'
        ).first()
        
        if pending_payment:
            # Reuse existing pending payment
            payment = pending_payment
        else:
            # Create new payment record
            payment = Payment.objects.create(
                user=order.user,
                order=order,
                amount=order.order_total,
                email=order.email,
                status='pending'
            )
        
        # Initialize with Paystack
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
            # Update payment with Paystack response data
            payment.paystack_reference = result.get('reference', payment.ref)
            payment.authorization_url = result.get('authorization_url')
            payment.access_code = result.get('access_code')
            payment.save()
            
            # Redirect to Paystack
            return redirect(payment.authorization_url)
        else:
            messages.error(
                request, 
                f"Payment initialization failed: {result.get('message', 'Unknown error')}"
            )
            return redirect('order_complete', order_number=order.order_number)  # Fixed: use order_number
            
    except Exception as e:
        logger.error(f"Error initializing payment for order {order_id}: {str(e)}")
        print(f"Full traceback in initialize_payment: {traceback.format_exc()}")
        messages.error(request, "An error occurred while processing your payment. Please try again.")
        return redirect('cart')


def verify_payment(request):
    reference = request.GET.get("reference")
    print(f"DEBUG: Starting verify_payment with reference: {reference}")
    
    if not reference:
        messages.error(request, "No payment reference provided.")
        return redirect('cart')
    
    try:
        # Find payment by reference
        payment = Payment.objects.filter(
            models.Q(ref=reference) | models.Q(paystack_reference=reference)
        ).first()
        
        print(f"DEBUG: Found payment: {payment}")
        
        if not payment:
            messages.error(request, "Payment record not found.")
            return redirect('cart')
        
        print(f"DEBUG: About to call payment.verify_payment()")
        
        # Verify the payment - THIS IS WHERE THE ERROR IS LIKELY HAPPENING
        try:
            verified = payment.verify_payment()
            print(f"DEBUG: Payment verification result: {verified}")
        except Exception as verify_error:
            print(f"DEBUG: Error in payment.verify_payment(): {str(verify_error)}")
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            messages.error(request, "Payment verification failed due to system error.")
            return redirect('cart')
        
        if verified and payment.is_successful():
            print(f"DEBUG: Payment verified successfully, clearing cart")
            
            # Clear cart
            if request.user.is_authenticated:
                CartItem.objects.filter(user=request.user, is_active=True).delete()
            else:
                try:
                    cart = Cart.objects.get(cart_id=_cart_id(request))
                    CartItem.objects.filter(cart=cart, is_active=True).delete()
                    cart.delete()  # Delete guest cart
                except Cart.DoesNotExist:
                    pass
            
            # Prepare context for success page
            context = {
                "payment": payment,
                "order": payment.order,
                "success": True
            }
            
            print(f"DEBUG: About to render payment_success.html")
            messages.success(request, f"Payment successful! Order {payment.order.order_number} has been confirmed.")
            return render(request, "payment/payment_success.html", context)
        else:
            print(f"DEBUG: Payment verification failed or not successful")
            messages.error(request, "Payment verification failed. Please contact support if you were charged.")
            context = {
                "payment": payment,
                "order": payment.order,
                "success": False
            }
            return render(request, "payment/payment_failed.html", context)
            
    except Exception as e:
        logger.error(f"Error verifying payment {reference}: {str(e)}")
        print(f"DEBUG: Exception in verify_payment: {str(e)}")
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        messages.error(request, "An error occurred while verifying your payment. Please contact support.")
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