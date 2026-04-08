from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
import uuid

User = get_user_model()


class Visitor(models.Model):
    """Track unique visitors"""
    session_id = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    page_views = models.PositiveIntegerField(default=1)
    first_visit = models.DateTimeField(auto_now_add=True)
    last_visit = models.DateTimeField(auto_now=True)
    is_unique = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-last_visit']
        indexes = [
            models.Index(fields=['-first_visit']),
            models.Index(fields=['-last_visit']),
        ]
    
    def __str__(self):
        return f"Visitor {self.session_id[:8]} - {self.ip_address}"


class PageView(models.Model):
    """Track individual page views"""
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE, related_name='views')
    path = models.CharField(max_length=500)
    title = models.CharField(max_length=500, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['-viewed_at']),
            models.Index(fields=['path', '-viewed_at']),
        ]


class DailyStats(models.Model):
    """Aggregate daily statistics"""
    date = models.DateField(unique=True)
    unique_visitors = models.PositiveIntegerField(default=0)
    total_visits = models.PositiveIntegerField(default=0)
    page_views = models.PositiveIntegerField(default=0)
    
    # Sales stats
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Product stats
    new_products = models.PositiveIntegerField(default=0)
    out_of_stock = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Daily Stats'
    
    def __str__(self):
        return f"Stats for {self.date}"


class SalesAnalytics:
    """Helper class for sales analytics"""
    
    @staticmethod
    def get_period_stats(days=30):
        """Get stats for a period"""
        from orders.models import Order
        from store.models import Product
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        
        orders = Order.objects.filter(created_at__date__gte=start_date)
        
        return {
            'total_orders': orders.count(),
            'completed_orders': orders.filter(status='Completed').count(),
            'pending_orders': orders.filter(status='Pending Payment').count(),
            'total_revenue': orders.filter(status='Completed').aggregate(
                total=Sum('order_total')
            )['total'] or 0,
            'average_order_value': orders.filter(status='Completed').aggregate(
                avg=Sum('order_total')
            )['avg'] or 0,
            'products_count': Product.objects.filter(is_available=True).count(),
            'out_of_stock': Product.objects.filter(stock=0, is_available=True).count(),
        }
    
    @staticmethod
    def get_daily_sales(days=30):
        """Get daily sales data for charts"""
        from orders.models import Order
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        data = []
        
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            orders = Order.objects.filter(
                created_at__date=date,
                status='Completed'
            )
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'label': date.strftime('%b %d'),
                'orders': orders.count(),
                'revenue': float(orders.aggregate(total=Sum('order_total'))['total'] or 0),
            })
        
        return data
    
    @staticmethod
    def get_top_products(limit=10):
        """Get top selling products"""
        from orders.models import OrderProduct
        from django.db.models import Sum, Count
        
        return OrderProduct.objects.filter(
            ordered=True
        ).values(
            'product__product_name',
            'product__id'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum('product_price')
        ).order_by('-total_sold')[:limit]
    
    @staticmethod
    def get_orders_by_status():
        """Get orders grouped by status"""
        from orders.models import Order
        return Order.objects.values('status').annotate(count=Count('id'))


class VisitorAnalytics:
    """Helper class for visitor analytics"""
    
    @staticmethod
    def get_visitor_stats(days=30):
        """Get visitor stats for a period"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        
        visitors = Visitor.objects.filter(first_visit__date__gte=start_date)
        
        return {
            'unique_visitors': visitors.filter(is_unique=True).count(),
            'total_visits': visitors.count(),
            'page_views': PageView.objects.filter(
                viewed_at__date__gte=start_date
            ).count(),
        }
    
    @staticmethod
    def get_daily_visitors(days=30):
        """Get daily visitor data for charts"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        data = []
        
        for i in range(days - 1, -1, -1):
            date = today - timedelta(days=i)
            visitors = Visitor.objects.filter(first_visit__date=date)
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'label': date.strftime('%b %d'),
                'visitors': visitors.count(),
                'page_views': PageView.objects.filter(viewed_at__date=date).count(),
            })
        
        return data
    
    @staticmethod
    def get_popular_pages(limit=10):
        """Get most popular pages"""
        from django.db.models import Count
        
        return PageView.objects.values('path').annotate(
            views=Count('id')
        ).order_by('-views')[:limit]
