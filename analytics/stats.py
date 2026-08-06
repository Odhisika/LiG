from django.utils import timezone
from datetime import timedelta


def _delta(current, previous):
    """Percentage change between previous and current period.

    Returns None when both values are zero/absent (nothing to compare),
    100.0 when the previous period was empty but current has activity.
    """
    if current in (None, 0) and previous in (None, 0):
        return None
    if previous in (None, 0):
        return 100.0
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def _unique_visitors(queryset):
    """Count real users: drop bots and collapse sessions by IP + User-Agent."""
    from .bot_detection import bot_q
    return queryset.exclude(bot_q()).values('ip_address', 'user_agent').distinct().count()


def _real_page_views(queryset):
    """Count page views from non-bot visitors."""
    from .bot_detection import bot_q
    return queryset.exclude(bot_q('visitor__user_agent')).count()


def _period_stats(start, end):
    """Aggregate sales/visitor stats for orders in [start, end) date range."""
    from orders.models import Order
    from accounts.models import Account
    from payment.models import Payment
    from .models import Visitor, PageView
    from django.db.models import Sum

    orders = Order.objects.filter(
        created_at__date__gte=start,
        created_at__date__lt=end,
    )
    completed = orders.filter(status='Completed')
    revenue = completed.aggregate(total=Sum('order_total'))['total'] or 0
    completed_count = completed.count()

    payments = Payment.objects.filter(
        created_at__date__gte=start,
        created_at__date__lt=end,
    )
    payment_total = payments.count()
    payment_success = payments.filter(status='successful').count()

    return {
        'revenue': revenue,
        'orders': orders.count(),
        'completed': completed_count,
        'pending': orders.filter(status='Pending Payment').count(),
        'cancelled': orders.filter(status='Cancelled').count(),
        'aov': (revenue / completed_count) if completed_count else 0,
        'visitors': _unique_visitors(Visitor.objects.filter(
            first_visit__date__gte=start,
            first_visit__date__lt=end,
        )),
        'page_views': _real_page_views(PageView.objects.filter(
            viewed_at__date__gte=start,
            viewed_at__date__lt=end,
        )),
        'new_customers': Account.objects.filter(
            date_joined__date__gte=start,
            date_joined__date__lt=end,
        ).count(),
        'payment_total': payment_total,
        'payment_success': payment_success,
        'payment_success_rate': (payment_success / payment_total * 100) if payment_total else 0,
    }


def get_index_stats(days=30):
    """Compute dashboard stat cards for the current vs previous period.

    Current period: last ``days`` days (including today).
    Previous period: the ``days`` days immediately before that.
    """
    from orders.models import OrderProduct
    from store.models import Product
    from .models import Visitor
    from django.db.models import F, Sum

    today = timezone.now().date()
    start = today - timedelta(days=days)
    end = today + timedelta(days=1)
    prev_end = start
    prev_start = start - timedelta(days=days)

    current = _period_stats(start, end)
    previous = _period_stats(prev_start, prev_end)

    conversion_rate = (current['completed'] / current['visitors'] * 100) if current['visitors'] else 0
    prev_conversion = (previous['completed'] / previous['visitors'] * 100) if previous['visitors'] else 0

    today_visitors = _unique_visitors(Visitor.objects.filter(first_visit__date=today))

    top_categories = OrderProduct.objects.filter(
        ordered=True,
        order__created_at__date__gte=start,
        order__created_at__date__lt=end,
    ).values(
        'product__category__category_name'
    ).annotate(
        units=Sum('quantity'),
        revenue=Sum(F('product_price') * F('quantity')),
    ).order_by('-units')[:5]

    low_stock = Product.objects.filter(stock__lte=5, stock__gt=0, is_available=True).count()
    out_of_stock = Product.objects.filter(stock=0, is_available=True).count()

    def pct(key):
        return _delta(current[key], previous[key])

    return {
        'days': days,
        # Sales
        'revenue': float(current['revenue']),
        'revenue_delta': pct('revenue'),
        'orders': current['orders'],
        'orders_delta': pct('orders'),
        'completed': current['completed'],
        'aov': float(current['aov']),
        'aov_delta': pct('aov'),
        'conversion_rate': round(conversion_rate, 2),
        'conversion_delta': _delta(conversion_rate, prev_conversion),
        'cancelled': current['cancelled'],
        'cancelled_delta': pct('cancelled'),
        'pending': current['pending'],
        'pending_delta': pct('pending'),
        # Customers
        'new_customers': current['new_customers'],
        'new_customers_delta': pct('new_customers'),
        # Visitors
        'visitors': current['visitors'],
        'visitors_delta': pct('visitors'),
        'page_views': current['page_views'],
        'today_visitors': today_visitors,
        # Payments
        'payment_success_rate': round(current['payment_success_rate'], 2),
        'payment_success_delta': _delta(current['payment_success_rate'], previous['payment_success_rate']),
        # Products
        'top_categories': list(top_categories),
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
    }
