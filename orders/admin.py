from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderProduct, PaymentProof
from .emails import send_order_status_email


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('user', 'product', 'quantity', 'product_price', 'ordered')  # Removed 'payment'
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'full_name', 'phone', 'city', 'order_total',
        'payment_status', 'status', 'paid', 'created_at',
    ]
    list_editable = ['status']
    list_filter = ['status', 'paid', 'created_at']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline]

    fieldsets = (
        (None, {
            "fields": ("status_badge", "payment_status", "status"),
        }),
    )
    readonly_fields = ['status_badge', 'payment_status']

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'Pending':    ('#856404', '#fff3cd'),
            'In Transit': ('#1e40af', '#bfdbfe'),
            'Delivered':  ('#1a7a4a', '#d4edda'),
            'Cancelled':  ('#721c24', '#f8d7da'),
        }
        fg, bg = colours.get(obj.status, ('#383d41', '#e2e3e5'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:0.82em;font-weight:600;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.display(description='Payment')
    def payment_status(self, obj):
        payments = obj.payments.all()
        if obj.paid:
            label = 'Paid'
            fg, bg = '#1a7a4a', '#d4edda'
        elif payments.filter(status='failed').exists():
            label = 'Failed'
            fg, bg = '#721c24', '#f8d7da'
        elif payments.exists():
            label = 'Pending'
            fg, bg = '#856404', '#fff3cd'
        else:
            label = 'Unpaid'
            fg, bg = '#383d41', '#e2e3e5'
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:0.82em;font-weight:600;">{}</span>',
            bg, fg, label,
        )

    def save_model(self, request, obj, form, change):
        old_status = None
        if obj.pk and change:
            try:
                old_status = Order.objects.get(pk=obj.pk).status
            except Order.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if old_status and old_status != obj.status:
            try:
                send_order_status_email(obj, old_status, obj.status)
            except Exception:
                pass


class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ['user', 'order', 'proof_image', 'note', 'status', 'submitted_at']
    list_editable = ['status']
    list_filter = ['status', 'submitted_at']
    search_fields = ['user__username', 'order__order_number']


admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)
admin.site.register(PaymentProof, PaymentProofAdmin)
