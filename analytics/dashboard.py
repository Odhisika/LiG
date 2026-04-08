from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import json


class DashboardSite(AdminSite):
    site_header = "LiG Store Administration"
    site_title = "LiG Admin"
    index_title = "Dashboard"
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        urls += [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        return urls
    
    def dashboard_view(self, request):
        from orders.models import Order
        from store.models import Product
        from accounts.models import Account
        from payment.models import Payment
        from .models import Visitor, PageView
        
        today = timezone.now().date()
        
        # Period filters
        period = request.GET.get('period', '30')
        try:
            days = int(period)
        except:
            days = 30
        
        start_date = today - timedelta(days=days)
        
        # Sales Stats
        orders = Order.objects.filter(created_at__date__gte=start_date)
        completed_orders = orders.filter(status='Completed')
        
        total_revenue = completed_orders.aggregate(total=Sum('order_total'))['total'] or 0
        total_orders = orders.count()
        completed_count = completed_orders.count()
        pending_orders = orders.filter(status='Pending Payment').count()
        
        # Products Stats
        total_products = Product.objects.filter(is_available=True).count()
        out_of_stock = Product.objects.filter(stock=0, is_available=True).count()
        low_stock = Product.objects.filter(stock__lte=5, stock__gt=0, is_available=True).count()
        
        # Users Stats
        total_users = Account.objects.filter(is_active=True).count()
        new_users = Account.objects.filter(date_joined__date__gte=start_date).count()
        
        # Visitor Stats
        visitors = Visitor.objects.filter(first_visit__date__gte=start_date)
        total_visitors = visitors.count()
        page_views = PageView.objects.filter(viewed_at__date__gte=start_date).count()
        
        # Daily Sales Data for Chart (last 30 days)
        daily_sales = []
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            day_orders = completed_orders.filter(created_at__date=date)
            daily_sales.append({
                'date': date.strftime('%Y-%m-%d'),
                'label': date.strftime('%b %d'),
                'orders': day_orders.count(),
                'revenue': float(day_orders.aggregate(total=Sum('order_total'))['total'] or 0),
            })
        
        # Daily Visitors Data
        daily_visitors = []
        for i in range(29, -1, -1):
            date = today - timedelta(days=i)
            day_visitors = visitors.filter(first_visit__date=date)
            daily_visitors.append({
                'date': date.strftime('%Y-%m-%d'),
                'visitors': day_visitors.count(),
                'page_views': PageView.objects.filter(viewed_at__date=date).count(),
            })
        
        # Top Selling Products
        from orders.models import OrderProduct
        top_products = OrderProduct.objects.filter(
            ordered=True,
            order__created_at__date__gte=start_date
        ).values(
            'product__product_name',
            'product__id'
        ).annotate(
            total_sold=Sum('quantity')
        ).order_by('-total_sold')[:5]
        
        # Orders by Status
        orders_by_status = orders.values('status').annotate(count=Count('id'))
        
        # Recent Orders
        recent_orders = Order.objects.all().order_by('-created_at')[:10]
        
        # Recent Payments
        recent_payments = Payment.objects.filter(status='successful').order_by('-created_at')[:10]
        
        context = {
            **self.each_context(request),
            'title': 'Dashboard',
            
            # Period Stats
            'period': period,
            'days': days,
            
            # Sales
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'completed_orders': completed_count,
            'pending_orders': pending_orders,
            
            # Products
            'total_products': total_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            
            # Users
            'total_users': total_users,
            'new_users': new_users,
            
            # Visitors
            'total_visitors': total_visitors,
            'page_views': page_views,
            
            # Chart Data
            'daily_sales_json': json.dumps(daily_sales),
            'daily_visitors_json': json.dumps(daily_visitors),
            
            # Other Data
            'top_products': list(top_products),
            'orders_by_status': list(orders_by_status),
            'recent_orders': recent_orders,
            'recent_payments': recent_payments,
        }
        
        return render(request, 'admin/dashboard.html', context)


# Create instance
dashboard_site = DashboardSite(name='dashboard')
