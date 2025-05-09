from django.contrib import admin
from .models import  Order, OrderProduct, PaymentProof

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('user', 'product', 'quantity', 'product_price', 'ordered')  # Removed 'payment'
    extra = 0

class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'tax', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline]

class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ['user', 'order', 'proof_image', 'note', 'status', 'submitted_at']
    list_editable = ['status']
    list_filter = ['status', 'submitted_at']
    search_fields = ['user__username', 'order__order_number']



admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)
admin.site.register(PaymentProof, PaymentProofAdmin)

