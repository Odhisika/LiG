import time
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from accounts.utils.csp import build_csp_policy
from accounts.utils.audit import log_action


class AdminAutoLogoutMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return
        if request.user.is_superuser or request.user.is_staff:
            current_time = time.time()
            last_activity = request.session.get('admin_last_activity')
            timeout = getattr(settings, 'ADMIN_SESSION_EXPIRE_SECONDS', 3600)
            if last_activity and (current_time - last_activity) > timeout:
                log_action(request.user, 'LOGOUT', request, details='Session timeout')
                logout(request)
                if 'admin_last_activity' in request.session:
                    del request.session['admin_last_activity']
            else:
                request.session['admin_last_activity'] = current_time


class SecurityHeadersMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        csp = build_csp_policy(request)
        response['Content-Security-Policy'] = csp
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=()'
        return response


class AuditMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if hasattr(request, 'user') and request.user.is_authenticated:
            path = request.path_info
            if path.startswith('/securelogin/') and request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                func_name = getattr(view_func, '__name__', '')
                if func_name not in ('login', 'logout', ''):
                    log_action(
                        request.user, 'ADMIN_ACTION', request,
                        target_model='admin',
                        details=f'{request.method} {path}'
                    )
        return None
