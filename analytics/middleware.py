import uuid
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.http import JsonResponse


class VisitorTrackingMiddleware(MiddlewareMixin):
    """Middleware to track visitors and page views"""
    
    def process_request(self, request):
        # Skip admin and static files
        if request.path.startswith('/admin') or \
           request.path.startswith('/static') or \
           request.path.startswith('/media') or \
           request.path.startswith('/securelogin'):
            return None
        
        # Skip AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
        
        from analytics.models import Visitor, PageView
        
        # Get or create session ID
        if not request.session.session_key:
            request.session.create()
        
        session_id = request.session.session_key
        
        # Get visitor info
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        referrer = request.META.get('HTTP_REFERER', '')[:500]
        
        # Create or update visitor
        visitor, created = Visitor.objects.get_or_create(
            session_id=session_id,
            defaults={
                'ip_address': ip_address,
                'user_agent': user_agent,
                'referrer': referrer,
            }
        )
        
        # Update visitor
        if not created:
            visitor.page_views += 1
            visitor.last_visit = timezone.now()
            visitor.save()
        
        # Record page view (limit to avoid too many records)
        path = request.path[:500]
        title = request.path
        
        # Only save every 10th page view to reduce DB load
        if visitor.page_views % 10 == 1:  # Save on 1st, 11th, 21st, etc.
            PageView.objects.create(
                visitor=visitor,
                path=path,
                title=title
            )
        
        # Store visitor in request for use in views
        request.visitor = visitor
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
