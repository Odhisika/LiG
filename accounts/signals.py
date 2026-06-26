from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from accounts.models import Account, AuditLog
from accounts.utils.audit import log_action


@receiver(user_login_failed)
def handle_failed_login(sender, credentials, request, **kwargs):
    email = credentials.get('username', '')
    try:
        user = Account.objects.get(email=email)
    except Account.DoesNotExist:
        user = None
    log_action(user, 'LOGIN_FAILED', request, details=f'Failed login attempt for {email}')


@receiver(user_logged_in)
def handle_login(sender, request, user, **kwargs):
    action = 'ADMIN_LOGIN_SUCCESS' if (user.is_staff or user.is_superuser) else 'LOGIN_SUCCESS'
    log_action(user, action, request)


@receiver(user_logged_out)
def handle_logout(sender, request, user, **kwargs):
    if user:
        action = 'ADMIN_ACTION' if (user.is_staff or user.is_superuser) else 'LOGOUT'
        log_action(user, action, request)
