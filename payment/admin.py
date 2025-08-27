# payment/admin.py (Optional - for Django admin)
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['ref', 'order', 'user', 'amount', 'status', 'verified', 'created_at']
    list_filter = ['status', 'verified', 'channel', 'created_at']
    search_fields = ['ref', 'paystack_reference', 'order__order_number', 'user__email']
    readonly_fields = ['ref', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user', 'order', 'amount', 'email', 'ref')
        }),
        ('Status', {
            'fields': ('status', 'verified')
        }),
        ('Paystack Data', {
            'fields': ('paystack_reference', 'authorization_url', 'access_code')
        }),
        ('Transaction Details', {
            'fields': ('channel', 'currency', 'transaction_date', 'card_type', 'bank', 'last4', 'paystack_fees')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )