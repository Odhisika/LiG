import uuid
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Account
from category.models import Category
from orders.models import Order, OrderProduct
from payment.models import Payment
from store.models import Product

from .models import Visitor, PageView
from .stats import get_index_stats


class IndexStatsTests(TestCase):
    def setUp(self):
        self.today = timezone.now()
        self.cat = Category.objects.create(category_name='Laptops', slug='laptops')
        self.product = Product.objects.create(
            product_name='Test Laptop',
            slug='test-laptop',
            price=Decimal('100.00'),
            stock=10,
            category=self.cat,
        )
        self.product_out = Product.objects.create(
            product_name='Out of Stock Item',
            slug='out-of-stock-item',
            price=Decimal('50.00'),
            stock=0,
            category=self.cat,
        )
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser',
            email='test@example.com', password='secret123',
        )
        self.user.is_active = True
        self.user.save()

    def _make_order(self, status, total, days_ago):
        order = Order.objects.create(
            user=self.user,
            order_number=f'ORD-{uuid.uuid4().hex[:8]}',
            first_name='Test', last_name='User',
            phone='0240000000', email='test@example.com',
            address_line_1='1 Test St', country='GH', state='GA', city='Accra',
            order_total=Decimal(str(total)), tax=Decimal('0.00'),
            status=status, is_ordered=True,
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=self.today - timedelta(days=days_ago)
        )
        return order

    def test_returns_all_expected_keys(self):
        stats = get_index_stats()
        for key in (
            'days', 'revenue', 'revenue_delta', 'orders', 'orders_delta',
            'completed', 'aov', 'aov_delta', 'conversion_rate',
            'conversion_delta', 'cancelled', 'cancelled_delta', 'pending',
            'pending_delta', 'new_customers', 'new_customers_delta',
            'visitors', 'visitors_delta', 'page_views', 'today_visitors',
            'payment_success_rate', 'payment_success_delta',
            'top_categories', 'low_stock', 'out_of_stock',
        ):
            self.assertIn(key, stats)
        self.assertEqual(stats['days'], 30)

    def test_current_period_totals(self):
        self._make_order('Completed', 100, 0)
        self._make_order('Pending Payment', 50, 0)
        Visitor.objects.create(session_id='sess-today')

        stats = get_index_stats()
        self.assertEqual(stats['revenue'], 100.0)
        self.assertEqual(stats['orders'], 2)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['aov'], 100.0)
        self.assertEqual(stats['visitors'], 1)
        self.assertEqual(stats['today_visitors'], 1)
        self.assertEqual(stats['new_customers'], 1)
        self.assertEqual(stats['conversion_rate'], 100.0)
        self.assertEqual(stats['low_stock'], 0)
        self.assertEqual(stats['out_of_stock'], 1)

    def test_payment_success_rate(self):
        order = self._make_order('Completed', 100, 0)
        Payment.objects.create(
            user=self.user, order=order, amount=Decimal('100.00'),
            ref=f'PAY-{uuid.uuid4().hex[:8]}', email='test@example.com',
            status='successful',
        )
        stats = get_index_stats()
        self.assertEqual(stats['payment_success_rate'], 100.0)

    def test_delta_between_periods(self):
        self._make_order('Completed', 50, 45)
        self._make_order('Completed', 100, 0)

        stats = get_index_stats()
        self.assertEqual(stats['revenue'], 100.0)
        self.assertEqual(stats['revenue_delta'], 100.0)

    def test_top_categories(self):
        order = self._make_order('Completed', 200, 0)
        OrderProduct.objects.create(
            order=order, user=self.user, product=self.product,
            quantity=2, product_price=Decimal('100.00'), ordered=True,
        )
        stats = get_index_stats()
        self.assertEqual(len(stats['top_categories']), 1)
        top = stats['top_categories'][0]
        self.assertEqual(top['product__category__category_name'], 'Laptops')
        self.assertEqual(top['units'], 2)
        self.assertEqual(float(top['revenue']), 200.0)

    def test_no_data_returns_zero_values(self):
        stats = get_index_stats()
        self.assertEqual(stats['revenue'], 0.0)
        self.assertEqual(stats['orders'], 0)
        self.assertEqual(stats['visitors'], 0)
        self.assertIsNone(stats['revenue_delta'])


class AdminIndexViewTests(TestCase):
    def setUp(self):
        self.admin = Account.objects.create_superuser(
            email='admin@example.com', username='admin', password='admin12345',
        )

    def test_index_renders_with_stats(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('admin_stats', response.context)
        self.assertEqual(response.context['admin_stats']['days'], 30)

    def test_index_respects_period_param(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:index'), {'period': '7'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['admin_stats']['days'], 7)
