from django.core.cache import cache
from django.conf import settings


LOCKOUT_MAX_ATTEMPTS = getattr(settings, 'LOCKOUT_MAX_ATTEMPTS', 5)
LOCKOUT_DURATION = getattr(settings, 'LOCKOUT_DURATION', 900)


def _key(username, ip):
    return f'login_attempts:{username}:{ip}'


def record_failed_attempt(username, ip):
    key = _key(username, ip)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOCKOUT_DURATION)
    return attempts


def is_locked_out(username, ip):
    key = _key(username, ip)
    attempts = cache.get(key, 0)
    return attempts >= LOCKOUT_MAX_ATTEMPTS


def get_remaining_attempts(username, ip):
    key = _key(username, ip)
    attempts = cache.get(key, 0)
    return max(0, LOCKOUT_MAX_ATTEMPTS - attempts)


def clear_attempts(username, ip):
    key = _key(username, ip)
    cache.delete(key)
