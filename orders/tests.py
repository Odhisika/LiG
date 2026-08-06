from decimal import Decimal
from types import SimpleNamespace
from django.test import TestCase
from django.core import mail
from django.urls import reverse
from django.contrib import admin as django_admin
from accounts.models import Account
from orders.models import Order, OrderProduct, PaymentProof
from orders.admin import OrderAdmin
from store.models import Product
from category.models import Category


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Test',
            last_name='User',
            username='testorderuser',
            email='testorder@example.com',
            password='Password123!',
        )
        self.cat = Category.objects.create(category_name='Hardware', slug='hardware')
        self.product = Product.objects.create(
            product_name='Test Item',
            slug='test-item',
            price=Decimal('150.00'),
            stock=10,
            category=self.cat,
        )
        self.order = Order.objects.create(
            user=self.user,
            order_number='2026080501',
            first_name='Test',
            last_name='User',
            phone='0240000000',
            email='testorder@example.com',
            address_line_1='123 Main St',
            country='Ghana',
            state='Greater Accra',
            city='Accra',
            order_total=Decimal('150.00'),
            tax=Decimal('0.00'),
            status='Pending Payment',
            is_ordered=True,
        )

    def test_order_str(self):
        self.assertEqual(str(self.order), "Order 2026080501 - Pending Payment")

    def test_order_full_name(self):
        self.assertEqual(self.order.full_name(), "Test User")

    def test_order_full_address(self):
        self.assertIn("123 Main St", self.order.full_address())

    def test_order_product_str(self):
        item = OrderProduct.objects.create(
            order=self.order,
            user=self.user,
            product=self.product,
            quantity=2,
            product_price=Decimal('150.00'),
            ordered=True,
        )
        self.assertEqual(str(item), "Test Item (x2)")


class OrderAdminEmailTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Test',
            last_name='User',
            username='testorderadmin',
            email='testorder@example.com',
            password='Password123!',
        )
        self.order = Order.objects.create(
            user=self.user,
            order_number='2026080502',
            first_name='Test',
            last_name='User',
            phone='0240000000',
            email='testorder@example.com',
            address_line_1='123 Main St',
            country='Ghana',
            state='Greater Accra',
            city='Accra',
            order_total=Decimal('150.00'),
            tax=Decimal('0.00'),
            status='Pending',
            is_ordered=True,
        )

    def test_status_change_sends_email(self):
        admin_obj = OrderAdmin(model=Order, admin_site=django_admin.site)
        request = SimpleNamespace(user=self.user)

        self.order.status = 'In Transit'
        admin_obj.save_model(request, self.order, None, True)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('In Transit', mail.outbox[0].subject)
        self.assertIn(self.order.email, mail.outbox[0].to)

    def test_unchanged_status_sends_no_email(self):
        admin_obj = OrderAdmin(model=Order, admin_site=django_admin.site)
        request = SimpleNamespace(user=self.user)

        self.order.status = 'Pending'
        admin_obj.save_model(request, self.order, None, True)

        self.assertEqual(len(mail.outbox), 0)


class OrderUserViewsTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Test',
            last_name='User',
            username='testorderview',
            email='testorder@example.com',
            password='Password123!',
        )
        self.user.is_active = True
        self.user.save()
        self.order = Order.objects.create(
            user=self.user,
            order_number='2026080503',
            first_name='Test',
            last_name='User',
            phone='0240000000',
            email='testorder@example.com',
            address_line_1='123 Main St',
            country='Ghana',
            state='Greater Accra',
            city='Accra',
            order_total=Decimal('150.00'),
            tax=Decimal('0.00'),
            status='In Transit',
            is_ordered=True,
        )

    def test_my_orders_shows_status(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'In Transit')
        self.assertContains(response, 'Payment Due')

    def test_order_detail_shows_status(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('order_detail', args=[self.order.order_number]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'In Transit')
        self.assertContains(response, 'Payment Due')

