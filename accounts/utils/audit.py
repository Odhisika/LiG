from accounts.models import AuditLog


def log_action(user, action, request=None, target_model='', target_id='', details=''):
    ip = ''
    ua = ''
    if request:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            ip = xff.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')
    AuditLog.objects.create(
        user=user,
        action=action,
        target_model=target_model,
        target_id=target_id,
        ip_address=ip,
        user_agent=ua,
        details=details,
    )
