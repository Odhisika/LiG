import hmac
import base64
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.admin.sites import AdminSite
from django.urls import path
from django.contrib.auth import authenticate, login as auth_login
import requests

from accounts.utils.audit import log_action
from accounts.utils.twofactor import verify_totp, generate_totp_secret, generate_qr_code, generate_backup_codes
from accounts.utils.lockout import is_locked_out, record_failed_attempt, clear_attempts, LOCKOUT_MAX_ATTEMPTS
from accounts.models import Admin2FA


original_login = AdminSite.login


def _clean_2fa_session(request):
    request.session.pop('2fa_pending', None)
    request.session.pop('2fa_email', None)
    request.session.pop('2fa_user_id', None)
    request.session.pop('2fa_password', None)


def _check_backup_code(twofa, code):
    for bc in twofa.backup_codes:
        if not bc.get('used') and hmac.compare_digest(bc['code'], code):
            bc['used'] = True
            twofa.save(update_fields=['backup_codes'])
            return True
    return False


def two_factor_view(request):
    if not request.session.get('2fa_pending'):
        return redirect('admin:login')

    email = request.session.get('2fa_email', '')
    user_id = request.session.get('2fa_user_id')
    password = request.session.get('2fa_password')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        if not user_id or not password:
            messages.error(request, 'Session expired. Please login again.')
            _clean_2fa_session(request)
            return redirect('admin:login')

        try:
            twofa = Admin2FA.objects.get(user_id=user_id)
        except Admin2FA.DoesNotExist:
            messages.error(request, '2FA configuration not found.')
            _clean_2fa_session(request)
            return redirect('admin:login')

        code_valid = verify_totp(twofa.totp_secret, code)
        backup_used = False if code_valid else _check_backup_code(twofa, code)

        if code_valid or backup_used:
            user = twofa.user
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            auth_login(request, user)
            log_action(user, '2FA_SUCCESS', request,
                       details='Admin 2FA via backup code' if backup_used else 'Admin 2FA via TOTP')
            log_action(user, 'ADMIN_LOGIN_SUCCESS', request)
            _clean_2fa_session(request)
            if backup_used:
                messages.warning(request, 'Logged in with a backup code. Please reconfigure your 2FA.')
            return redirect('admin:index')
        else:
            log_action(twofa.user, '2FA_FAILED', request, details='Invalid 2FA code')
            messages.error(request, 'Invalid verification code. Please try again.')

    return render(request, 'admin/2fa.html', {'email': email})


def two_factor_setup_view(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('admin:login')

    twofa, created = Admin2FA.objects.get_or_create(
        user=request.user,
        defaults={'totp_secret': generate_totp_secret(), 'backup_codes': generate_backup_codes()}
    )

    if request.method == 'POST':
        secret = generate_totp_secret()
        twofa.totp_secret = secret
        twofa.save(update_fields=['totp_secret'])
        qr_buf = generate_qr_code(secret, request.user.email)
        qr_b64 = base64.b64encode(qr_buf.getvalue()).decode()
        qr_data_url = f'data:image/png;base64,{qr_b64}'
        return render(request, 'admin/2fa_setup.html', {
            'twofa': twofa,
            'qr_data_url': qr_data_url,
            'secret': secret,
        })

    if twofa.is_enabled:
        return render(request, 'admin/2fa_setup.html', {'twofa': twofa})

    secret = generate_totp_secret()
    twofa.totp_secret = secret
    twofa.save(update_fields=['totp_secret'])
    qr_buf = generate_qr_code(secret, request.user.email)
    qr_b64 = base64.b64encode(qr_buf.getvalue()).decode()
    qr_data_url = f'data:image/png;base64,{qr_b64}'
    return render(request, 'admin/2fa_setup.html', {
        'twofa': twofa,
        'qr_data_url': qr_data_url,
        'secret': secret,
    })


def two_factor_verify_setup_view(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('admin:login')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        secret = request.POST.get('secret', '')

        if verify_totp(secret, code):
            twofa, _ = Admin2FA.objects.get_or_create(
                user=request.user,
                defaults={'totp_secret': secret, 'backup_codes': generate_backup_codes()}
            )
            twofa.totp_secret = secret
            twofa.is_enabled = True
            if not twofa.backup_codes:
                twofa.backup_codes = generate_backup_codes()
            twofa.save()
            log_action(request.user, '2FA_ENABLED', request, details='Admin enabled 2FA')
            messages.success(request, 'Two-factor authentication has been enabled.')
            return redirect('admin:2fa_setup')
        else:
            messages.error(request, 'Invalid code. Please try again.')
            return redirect('admin:2fa_setup')

    return redirect('admin:2fa_setup')


def two_factor_disable_view(request):
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return redirect('admin:login')

    if request.method == 'POST':
        try:
            twofa = Admin2FA.objects.get(user=request.user)
            twofa.is_enabled = False
            twofa.save()
            log_action(request.user, '2FA_DISABLED', request, details='Admin disabled 2FA')
            messages.success(request, 'Two-factor authentication has been disabled.')
        except Admin2FA.DoesNotExist:
            messages.error(request, '2FA is not configured.')

    return redirect('admin:2fa_setup')


admin_urls_original = AdminSite.get_urls


def admin_get_urls(self):
    urls = admin_urls_original(self)
    custom_urls = [
        path('2fa/', two_factor_view, name='2fa'),
        path('2fa/setup/', self.admin_view(two_factor_setup_view), name='2fa_setup'),
        path('2fa/verify-setup/', self.admin_view(two_factor_verify_setup_view), name='2fa_verify_setup'),
        path('2fa/disable/', self.admin_view(two_factor_disable_view), name='2fa_disable'),
    ]
    return custom_urls + urls


AdminSite.get_urls = admin_get_urls


def admin_login_with_turnstile_and_2fa(self, request, extra_context=None):
    if request.method == 'GET' and request.session.get('2fa_pending'):
        return redirect('admin:2fa')

    if request.method == 'POST':
        token = request.POST.get('cf-turnstile-response', '')
        if not token:
            messages.error(request, 'Please complete the security check.')
            return redirect('admin:login')
        resp = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': settings.TURNSTILE_SECRET_KEY,
                'response': token,
            },
        )
        if not resp.json().get('success', False):
            messages.error(request, 'Security check failed. Please try again.')
            return redirect('admin:login')

        username = request.POST.get('username')
        password = request.POST.get('password')
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')

        if is_locked_out(username, ip):
            messages.error(request, 'Account temporarily locked due to too many failed attempts. Try again in 15 minutes.')
            return redirect('admin:login')

        user = authenticate(request, username=username, password=password)

        if user is not None and (user.is_staff or user.is_superuser):
            clear_attempts(username, ip)
            try:
                twofa = Admin2FA.objects.get(user=user)
                if twofa.is_enabled:
                    request.session['2fa_pending'] = True
                    request.session['2fa_email'] = user.email
                    request.session['2fa_user_id'] = user.pk
                    request.session['2fa_password'] = password
                    log_action(user, 'ADMIN_2FA_REQUIRED', request,
                               details='2FA challenge presented')
                    return redirect('admin:2fa')
            except Admin2FA.DoesNotExist:
                pass
        else:
            record_failed_attempt(username, ip)

    extra_context = extra_context or {}
    extra_context['TURNSTILE_SITE_KEY'] = settings.TURNSTILE_SITE_KEY
    return original_login(self, request, extra_context=extra_context)


AdminSite.login = admin_login_with_turnstile_and_2fa
