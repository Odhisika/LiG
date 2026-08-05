from decimal import Decimal
from django.test import TestCase
from accounts.models import Account
from orders.models import Order, OrderProduct, PaymentProof
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

