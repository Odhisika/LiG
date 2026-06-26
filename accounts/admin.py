from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils.html import format_html
from django.http import HttpResponse, HttpResponseRedirect
import base64

from accounts.models import Account, UserProfile, Admin2FA, AuditLog, NewsletterSubscriber
from store.models import Product
from accounts.utils.twofactor import generate_totp_secret, generate_qr_code, verify_totp, generate_backup_codes
from accounts.utils.audit import log_action
from accounts.utils.email import send_html_email


class AccountAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'username', 'last_login', 'date_joined', 'is_active', 'two_factor_status')
    list_display_links = ('email', 'first_name', 'last_name')
    readonly_fields = ('last_login', 'date_joined')
    ordering = ('-date_joined',)

    filter_horizontal = ()
    list_filter = ('is_active', 'is_staff')
    fieldsets = (
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'username', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    def two_factor_status(self, obj):
        try:
            if obj.two_factor.is_enabled:
                return format_html('<span style="color:green;">Enabled</span>')
        except Admin2FA.DoesNotExist:
            pass
        return format_html('<span style="color:gray;">Disabled</span>')
    two_factor_status.short_description = '2FA'


class UserProfileAdmin(admin.ModelAdmin):
    def thumbnail(self, object):
        try:
            url = object.profile_picture.url
        except (ValueError, FileNotFoundError):
            url = ''
        if not url:
            return format_html('<span style="color:gray;">No image</span>')
        return format_html('<img src="{}" width="30" style="border-radius:50%;">'.format(url))
    thumbnail.short_description = 'Profile Picture'
    list_display = ('thumbnail', 'user', 'city', 'state', 'country')


@admin.register(Admin2FA)
class Admin2FAAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_enabled', 'created_at', 'updated_at')
    list_filter = ('is_enabled',)
    search_fields = ('user__email',)
    readonly_fields = ('totp_secret', 'backup_codes', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'user', 'ip_address', 'target_model')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'ip_address', 'details')
    readonly_fields = ('user', 'action', 'target_model', 'target_id', 'ip_address', 'user_agent', 'timestamp', 'details')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at', 'is_active')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
    actions = ['send_newsletter_action']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('send-newsletter/', self.admin_site.admin_view(self.send_newsletter_view), name='send-newsletter'),
        ]
        return custom_urls + urls

    def send_newsletter_action(self, request, queryset):
        active = queryset.filter(is_active=True)
        if not active.exists():
            self.message_user(request, 'No active subscribers selected.', level='WARNING')
            return
        ids = ','.join(str(s.id) for s in active)
        return HttpResponseRedirect(reverse('admin:send-newsletter') + f'?ids={ids}')
    send_newsletter_action.short_description = 'Send newsletter to selected subscribers'

    def send_newsletter_view(self, request):
        ids = request.GET.get('ids') or request.POST.get('ids', '')
        if ids:
            id_list = [i for i in ids.split(',') if i.strip()]
            subscribers = NewsletterSubscriber.objects.filter(id__in=id_list, is_active=True)
        else:
            subscribers = NewsletterSubscriber.objects.filter(is_active=True)
            ids = ''

        available_products = Product.objects.filter(is_available=True).order_by('product_name')

        selected_product_ids = []
        selected_products = []

        if request.method == 'POST':
            subject = request.POST.get('subject', '').strip()
            body = request.POST.get('body', '').strip()
            button_text = request.POST.get('button_text', '').strip()
            button_url = request.POST.get('button_url', '').strip()
            action = request.POST.get('action', '')
            selected_product_ids = [int(i) for i in request.POST.getlist('product_ids') if i.strip().isdigit()]
            selected_products = list(Product.objects.filter(id__in=selected_product_ids, is_available=True))

            if not subject or not body:
                messages.error(request, 'Subject and body are required.')
                return render(request, 'admin/send_newsletter.html', {
                    'subscriber_count': subscribers.count(),
                    'ids': ids,
                    'subject': subject,
                    'body': body,
                    'button_text': button_text,
                    'button_url': button_url,
                    'products': available_products,
                    'selected_product_ids': selected_product_ids,
                })

            ctx = {
                'subject': subject,
                'body': body,
                'button_text': button_text,
                'button_url': button_url,
                'featured_products': selected_products,
                'site_url': f'{request.scheme}://{request.get_host()}',
            }

            if action == 'test':
                send_html_email(subject, 'emails/promotion_email.html', ctx, [request.user.email])
                messages.success(request, f'Test email sent to {request.user.email}.')
                url = reverse('admin:send-newsletter')
                if ids:
                    url += f'?ids={ids}'
                return redirect(url)

            sent = 0
            for sub in subscribers.iterator():
                try:
                    send_html_email(subject, 'emails/promotion_email.html', ctx, [sub.email])
                    sent += 1
                except Exception as e:
                    self.message_user(request, f'Failed to send to {sub.email}: {e}', level='ERROR')

            messages.success(request, f'Newsletter sent to {sent} subscriber(s).')
            return redirect('admin:accounts_newslettersubscriber_changelist')

        return render(request, 'admin/send_newsletter.html', {
            'subscriber_count': subscribers.count(),
            'ids': ids,
            'subject': '',
            'body': '',
            'button_text': '',
            'button_url': '',
            'products': available_products,
            'selected_product_ids': [],
        })

admin.site.register(Account, AccountAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
