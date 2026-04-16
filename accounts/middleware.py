import time
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

class AdminAutoLogoutMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return

        # Only check timeout for admin users (staff or superusers)
        if request.user.is_superuser or request.user.is_staff:
            current_time = time.time()
            last_activity = request.session.get('admin_last_activity')
            
            # Fetch timeout from settings, or default to 1 hour (3600 seconds)
            timeout = getattr(settings, 'ADMIN_SESSION_EXPIRE_SECONDS', 3600)

            if last_activity and (current_time - last_activity) > timeout:
                logout(request)
                # optionally clear the session key just to be clean
                if 'admin_last_activity' in request.session:
                    del request.session['admin_last_activity']
            else:
                # Update the last activity time
                request.session['admin_last_activity'] = current_time
