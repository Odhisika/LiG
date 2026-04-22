# payment/models.py - Fixed verify_payment method
from django.db import models
from django.conf import settings
import secrets
import uuid
from datetime import datetime
from .paystack import Paystack
from .hubtel import Hubtel


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
            print(f"Error verifying payment {self.ref}: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
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
            print(f"Paystack verification error: {str(e)}")
            self.status = 'failed'
            self.save()
            return False

    def _verify_hubtel_payment(self, transaction_id=None):
        """Verify payment with Hubtel."""
        try:
            hubtel = Hubtel()
            reference = self.hubtel_token or self.ref
            status, result = hubtel.verify_transaction(reference, transaction_id)
            
            if status and result:
                self.verified = True
                self.status = 'successful'
                
                self.channel = result.get('channel', 'mobile_money')
                self.currency = result.get('currency', 'GHS')
                
                if result.get('paid_at'):
                    try:
                        self.transaction_date = datetime.fromisoformat(
                            result['paid_at'].replace('Z', '+00:00')
                        )
                    except:
                        pass
                
                # Store last 4 digits if available
                if result.get('last4'):
                    self.last4 = result.get('last4')
                
                self.save()
                self._update_order_status()
                return True
            else:
                self.status = 'pending' if result and result.get('status') == 'pending' else 'failed'
                self.save()
                return False
                
        except Exception as e:
            print(f"Hubtel verification error: {str(e)}")
            self.status = 'failed'
            self.save()
            return False

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