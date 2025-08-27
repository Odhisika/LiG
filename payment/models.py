# payment/models.py - Fixed verify_payment method
from django.db import models
from django.conf import settings
import secrets
import uuid
from datetime import datetime
from .paystack import Paystack


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
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

    # Paystack response data
    paystack_reference = models.CharField(max_length=250, blank=True, null=True)
    authorization_url = models.URLField(blank=True, null=True)
    access_code = models.CharField(max_length=250, blank=True, null=True)
    
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

    def verify_payment(self):
        """Verify payment with Paystack and update details."""
        try:
            paystack = Paystack()
            status, result = paystack.verify_payment(self.paystack_reference or self.ref)
            
            if status and result:
                # Check if amount matches
                paystack_amount = int(result.get('amount', 0))
                expected_amount = self.amount_in_pesewas()
                
                if paystack_amount >= expected_amount:  # Allow for small differences due to fees
                    self.verified = True
                    self.status = 'successful'
                    
                    # Store transaction details
                    self.channel = result.get('channel')
                    self.currency = result.get('currency')
                    
                    # Parse transaction date
                    if result.get('transaction_date'):
                        try:
                            self.transaction_date = datetime.fromisoformat(
                                result['transaction_date'].replace('Z', '+00:00')
                            )
                        except:
                            pass
                    
                    # Store authorization details if available
                    auth = result.get('authorization', {})
                    if auth:
                        self.card_type = auth.get('card_type')
                        self.bank = auth.get('bank')
                        self.last4 = auth.get('last4')
                    
                    # Store fees
                    if result.get('fees'):
                        self.paystack_fees = result['fees'] / 100  # Convert from pesewas
                    
                    self.save()
                    
                    # Update order status - THIS IS THE CRITICAL FIX
                    if self.order and not self.order.paid:
                        self.order.paid = True
                        self.order.status = "Completed"
                        self.order.is_ordered = True  # Add this line
                        self.order.save()
                    
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
            print(f"Error verifying payment {self.ref}: {str(e)}")
            # Add more detailed error logging
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            self.status = 'failed'
            self.save()
            return False

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