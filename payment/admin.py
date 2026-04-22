# payment/admin.py
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.timezone import now
from .models import Payment


# ---------------------------------------------------------------------------
# Proxy models – give Paystack & Hubtel their own admin menu entries
# ---------------------------------------------------------------------------

class PaystackPayment(Payment):
    """Proxy – shows only Paystack payments."""
    class Meta:
        proxy = True
        verbose_name = "Paystack Payment"
        verbose_name_plural = "💳  Paystack Payments"


class HubtelPayment(Payment):
    """Proxy – shows only Hubtel payments."""
    class Meta:
        proxy = True
        verbose_name = "Hubtel Payment"
        verbose_name_plural = "📱  Hubtel Payments"


# ---------------------------------------------------------------------------
# Shared admin actions
# ---------------------------------------------------------------------------

@admin.action(description="✅  Mark selected payments as Verified & Successful")
def mark_as_verified(modeladmin, request, queryset):
    updated = 0
    for payment in queryset.filter(verified=False):
        payment.verified = True
        payment.status = "successful"
        if not payment.transaction_date:
            payment.transaction_date = now()
        payment.save()
        payment._update_order_status()
        updated += 1
    modeladmin.message_user(
        request,
        f"{updated} payment(s) marked as verified and successful.",
        messages.SUCCESS,
    )


@admin.action(description="🔄  Re-verify selected payments via gateway API")
def reverify_via_api(modeladmin, request, queryset):
    success_count = 0
    fail_count = 0
    for payment in queryset.exclude(status="successful"):
        try:
            result = payment.verify_payment()
            if result:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            fail_count += 1
            modeladmin.message_user(
                request,
                f"Error verifying {payment.ref}: {e}",
                messages.WARNING,
            )
    if success_count:
        modeladmin.message_user(
            request,
            f"{success_count} payment(s) successfully verified via API.",
            messages.SUCCESS,
        )
    if fail_count:
        modeladmin.message_user(
            request,
            f"{fail_count} payment(s) could not be verified (check gateway logs).",
            messages.WARNING,
        )


@admin.action(description="❌  Mark selected payments as Failed")
def mark_as_failed(modeladmin, request, queryset):
    updated = queryset.exclude(status="failed").update(status="failed", verified=False)
    modeladmin.message_user(
        request,
        f"{updated} payment(s) marked as failed.",
        messages.WARNING,
    )


# ---------------------------------------------------------------------------
# Base admin – shared columns/config
# ---------------------------------------------------------------------------

class BasePaymentAdmin(admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_per_page = 30
    actions = [mark_as_verified, reverify_via_api, mark_as_failed]
    readonly_fields = [
        "ref", "created_at", "updated_at",
        "status_badge", "gateway_badge",
    ]

    # ------------------------------------------------------------------
    # Custom display helpers
    # ------------------------------------------------------------------
    @admin.display(description="Status")
    def status_badge(self, obj):
        colours = {
            "successful": ("#1a7a4a", "#d4edda"),
            "pending":    ("#856404", "#fff3cd"),
            "failed":     ("#721c24", "#f8d7da"),
            "cancelled":  ("#383d41", "#e2e3e5"),
        }
        fg, bg = colours.get(obj.status, ("#383d41", "#e2e3e5"))
        label = obj.get_status_display()
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:0.82em;font-weight:600;">{}</span>',
            bg, fg, label,
        )

    @admin.display(description="Gateway")
    def gateway_badge(self, obj):
        colours = {
            "paystack": ("#00b8d9", "#e6f9ff"),
            "hubtel":   ("#ff6600", "#fff0e6"),
        }
        fg, bg = colours.get(obj.gateway, ("#383d41", "#e2e3e5"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;'
            'font-size:0.82em;font-weight:600;">{}</span>',
            bg, fg, obj.get_gateway_display(),
        )

    @admin.display(description="Order")
    def order_link(self, obj):
        if obj.order:
            return format_html(
                '<a href="/admin/orders/order/{}/change/">{}</a>',
                obj.order.id,
                obj.order.order_number,
            )
        return "—"

    @admin.display(description="Verified", boolean=True)
    def is_verified(self, obj):
        return obj.verified


# ---------------------------------------------------------------------------
# All-Payments admin (base Payment model)
# ---------------------------------------------------------------------------

@admin.register(Payment)
class PaymentAdmin(BasePaymentAdmin):
    list_display  = [
        "ref", "order_link", "user", "amount", "gateway_badge",
        "status_badge", "is_verified", "created_at",
    ]
    list_filter   = ["gateway", "status", "verified", "created_at"]
    search_fields = [
        "ref", "paystack_reference", "hubtel_token",
        "order__order_number", "user__email", "email",
    ]

    fieldsets = (
        ("📋  Payment Overview", {
            "fields": ("ref", "user", "order_link", "amount", "email",
                       "gateway_badge", "status_badge", "verified"),
        }),
        ("⚙️  Edit Status", {
            "fields": ("status",),
            "description": (
                "You can manually override the payment status here. "
                "Use the bulk actions above to mark multiple payments at once."
            ),
        }),
        ("💳  Paystack Data", {
            "classes": ("collapse",),
            "fields": ("paystack_reference", "authorization_url", "access_code"),
        }),
        ("📱  Hubtel Data", {
            "classes": ("collapse",),
            "fields": ("hubtel_token", "hubtel_checkout_url"),
        }),
        ("🏦  Transaction Details", {
            "classes": ("collapse",),
            "fields": (
                "channel", "currency", "transaction_date",
                "card_type", "bank", "last4", "paystack_fees",
            ),
        }),
        ("🕐  Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )


# ---------------------------------------------------------------------------
# Paystack-only admin
# ---------------------------------------------------------------------------

@admin.register(PaystackPayment)
class PaystackPaymentAdmin(BasePaymentAdmin):
    list_display  = [
        "ref", "order_link", "user", "amount",
        "status_badge", "is_verified",
        "paystack_reference", "channel", "created_at",
    ]
    list_filter   = ["status", "verified", "channel", "created_at"]
    search_fields = [
        "ref", "paystack_reference",
        "order__order_number", "user__email", "email",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(gateway="paystack")

    fieldsets = (
        ("📋  Payment Overview", {
            "fields": ("ref", "user", "order_link", "amount", "email",
                       "status_badge", "verified"),
        }),
        ("⚙️  Edit Status", {
            "fields": ("status",),
            "description": (
                "Manually override the status, or use 'Re-verify via gateway API' "
                "to fetch the latest status from Paystack."
            ),
        }),
        ("💳  Paystack Reference", {
            "fields": ("paystack_reference", "authorization_url", "access_code"),
        }),
        ("🏦  Transaction Details", {
            "classes": ("collapse",),
            "fields": (
                "channel", "currency", "transaction_date",
                "card_type", "bank", "last4", "paystack_fees",
            ),
        }),
        ("🕐  Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )


# ---------------------------------------------------------------------------
# Hubtel-only admin
# ---------------------------------------------------------------------------

@admin.register(HubtelPayment)
class HubtelPaymentAdmin(BasePaymentAdmin):
    list_display  = [
        "ref", "order_link", "user", "amount",
        "status_badge", "is_verified",
        "hubtel_token", "created_at",
    ]
    list_filter   = ["status", "verified", "created_at"]
    search_fields = [
        "ref", "hubtel_token",
        "order__order_number", "user__email", "email",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(gateway="hubtel")

    fieldsets = (
        ("📋  Payment Overview", {
            "fields": ("ref", "user", "order_link", "amount", "email",
                       "status_badge", "verified"),
        }),
        ("⚙️  Edit Status", {
            "fields": ("status",),
            "description": (
                "Manually override the status, or use 'Re-verify via gateway API' "
                "to fetch the latest status from Hubtel."
            ),
        }),
        ("📱  Hubtel Reference", {
            "fields": ("hubtel_token", "hubtel_checkout_url"),
        }),
        ("🏦  Transaction Details", {
            "classes": ("collapse",),
            "fields": ("channel", "currency", "transaction_date", "last4"),
        }),
        ("🕐  Timestamps", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )