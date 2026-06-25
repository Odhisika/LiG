# payment/models.py - Fixed verify_payment method
from django.db import models
from django.conf import settings
import secrets
import uuid
from datetime import datetime
import logging
from .paystack import Paystack
from .hubtel import Hubtel

logger = logging.getLogger(__name__)


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    GATEWAY_CHOICES = [
        ('paystack', 'Paystack'),
        ('hubtel', 'Hubtel'),
    ]
    
    user = models.ForeignKey("accounts.Account", on_delete=models.CASCADE)
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # GHS
    ref = models.CharField(max_length=250, unique=True)
    email = models.EmailField(max_length=250)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Gateway selection
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='paystack')
    
    # Paystack response data
    paystack_reference = models.CharField(max_length=250, blank=True, null=True)
    authorization_url = models.URLField(blank=True, null=True)
    access_code = models.CharField(max_length=250, blank=True, null=True)
    
    # Hubtel response data
    hubtel_token = models.CharField(max_length=250, blank=True, null=True)
    hubtel_checkout_url = models.URLField(blank=True, null=True)
    
    # Transaction details (populated after verification)
    channel = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    card_type = models.CharField(max_length=50, blank=True, null=True)
    bank = models.CharField(max_length=100, blank=True, null=True)
    last4 = models.CharField(max_length=4, blank=True, null=True)
    paystack_fees = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ref']),
            models.Index(fields=['paystack_reference']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Payment {self.ref} - {self.order.order_number} - {self.amount} GHS"

    def save(self, *args, **kwargs):
        if not self.ref:
            while True:
                ref = f"PAY_{uuid.uuid4().hex[:12].upper()}"
                if not Payment.objects.filter(ref=ref).exists():
                    self.ref = ref
                    break
        super().save(*args, **kwargs)

    def amount_in_pesewas(self):
        """Return amount in pesewas (Paystack expects amount in kobo/pesewas)."""
        return int(self.amount * 100)

    def verify_payment(self, transaction_id=None):
        """Verify payment with Paystack or Hubtel based on gateway selection."""
        try:
            if self.gateway == 'hubtel':
                return self._verify_hubtel_payment(transaction_id)
            else:
                return self._verify_paystack_payment()
        except Exception as e:
            logger.error(f"Error verifying payment %s: %s", self.ref, str(e), exc_info=True)
            self.status = 'failed'
            self.save()
            return False

    def _verify_paystack_payment(self):
        """Verify payment with Paystack."""
        try:
            paystack = Paystack()
            status, result = paystack.verify_payment(self.paystack_reference or self.ref)
            
            if status and result:
                paystack_amount = int(result.get('amount', 0))
                expected_amount = self.amount_in_pesewas()
                
                if paystack_amount >= expected_amount:
                    self.verified = True
                    self.status = 'successful'
                    
                    self.channel = result.get('channel')
                    self.currency = result.get('currency')
                    
                    if result.get('transaction_date'):
                        try:
                            self.transaction_date = datetime.fromisoformat(
                                result['transaction_date'].replace('Z', '+00:00')
                            )
                        except:
                            pass
                    
                    auth = result.get('authorization', {})
                    if auth:
                        self.card_type = auth.get('card_type')
                        self.bank = auth.get('bank')
                        self.last4 = auth.get('last4')
                    
                    if result.get('fees'):
                        self.paystack_fees = result['fees'] / 100
                    
                    self.save()
                    self._update_order_status()
                    return True
                else:
                    self.status = 'failed'
                    self.save()
                    return False
            else:
                self.status = 'failed' 
                self.save()
                return False
                
        except Exception as e:
            logger.error("Paystack verification error: %s", str(e), exc_info=True)
            self.status = 'failed'
            self.save()
            return False

    def _verify_hubtel_payment(self, transaction_id=None):
        """Verify payment with Hubtel."""
        import logging
        log = logging.getLogger(__name__)
        try:
            hubtel = Hubtel()

            # clientReference is always our own PAY_xxx ref
            reference = self.ref

            # transaction_id is Hubtel's own checkout/sales ID stored in hubtel_token
            # Use it automatically if caller didn't pass one
            if not transaction_id and self.hubtel_token and not self.hubtel_token.startswith('PAY_'):
                transaction_id = self.hubtel_token
                log.info(f"Using stored hubtel_token as transaction_id: {transaction_id}")

            status, result = hubtel.verify_transaction(reference, transaction_id)


            if status and result:
                # Hubtel confirmed payment SUCCESS
                self.verified = True
                self.status = 'successful'

                self.channel  = result.get('channel', 'mobile_money')
                self.currency = result.get('currency', 'GHS')

                if result.get('paid_at'):
                    try:
                        self.transaction_date = datetime.fromisoformat(
                            result['paid_at'].replace('Z', '+00:00')
                        )
                    except Exception:
                        pass

                if result.get('last4'):
                    self.last4 = result.get('last4')

                self.save()
                self._update_order_status()
                log.info(f"Hubtel payment {self.ref} verified successfully.")
                return True

            else:
                # result is None (API error/network issue) OR Hubtel returned a non-success status
                result_status = (result or {}).get('status', '') if result else ''

                if result_status in ('failed', 'cancelled', 'rejected'):
                    # Hubtel explicitly says payment failed
                    self.status = 'failed'
                    self.save()
                    log.warning(f"Hubtel payment {self.ref} explicitly failed: {result}")
                else:
                    # API error, timeout, pending, or unknown — keep as pending
                    # DO NOT mark as failed; let the webhook confirm later
                    self.status = 'pending'
                    self.save()
                    log.warning(
                        f"Hubtel payment {self.ref} not yet confirmed. "
                        f"result_status='{result_status}'. Keeping as pending."
                    )
                return False

        except Exception as e:
            # Network error, timeout, etc. — never mark as failed here
            log.error(f"Hubtel verification exception for {self.ref}: {str(e)}")
            self.status = 'pending'   # keep pending; webhook will confirm
            self.save()
            return False

    def mark_hubtel_success(self, transaction_data=None):
        """Mark a Hubtel payment successful from webhook-confirmed data."""
        transaction_data = transaction_data or {}

        self.verified = True
        self.status = 'successful'
        self.channel = (
            transaction_data.get('channel') or
            transaction_data.get('paymentMethod') or
            transaction_data.get('PaymentMethod') or
            self.channel or
            'mobile_money'
        )
        self.currency = (
            transaction_data.get('currency') or
            transaction_data.get('Currency') or
            self.currency or
            'GHS'
        )

        paid_at = (
            transaction_data.get('paid_at') or
            transaction_data.get('transaction_date') or
            transaction_data.get('TransactionDate') or
            transaction_data.get('TransactionDateTime')
        )
        if paid_at:
            try:
                self.transaction_date = datetime.fromisoformat(
                    str(paid_at).replace('Z', '+00:00')
                )
            except Exception:
                pass

        last4 = transaction_data.get('last4') or transaction_data.get('Last4')
        if last4:
            self.last4 = last4

        transaction_id = (
            transaction_data.get('transaction_id') or
            transaction_data.get('TransactionId') or
            transaction_data.get('transactionId') or
            transaction_data.get('checkoutId') or
            transaction_data.get('CheckoutId')
        )
        if transaction_id:
            self.hubtel_token = transaction_id

        self.save()
        self._update_order_status()

    def _update_order_status(self):
        """Update order status after successful payment."""
        if self.order and not self.order.paid:
            self.order.paid = True
            self.order.status = "Completed"
            self.order.is_ordered = True
            self.order.save()

    def is_successful(self):
        return self.status == 'successful' and self.verified

    @classmethod
    def get_successful_payment_for_order(cls, order):
        """Get the successful payment for an order if it exists."""
        return cls.objects.filter(
            order=order, 
            status='successful', 
            verified=True
        ).first()
