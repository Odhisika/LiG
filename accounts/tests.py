from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Account
from cart.models import Cart, CartItem
from category.models import Category
from store.models import Product


class LoginRedirectTests(TestCase):
    def setUp(self):
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser',
            email='test@example.com', password='secret123',
        )
        self.user.is_active = True
        self.user.save()

    def _login(self, next_url=None):
        data = {'email': 'test@example.com', 'password': 'secret123'}
        url = reverse('login')
        if next_url:
            url = f'{url}?next={next_url}'
        return self.client.post(url, data)

    def _create_product(self):
        category = Category.objects.create(
            category_name='Test Category', slug='test-category',
        )
        return Product.objects.create(
            product_name='Test Product',
            slug='test-product',
            price=10,
            stock=5,
            category=category,
        )

    def _add_item_to_user_cart(self):
        CartItem.objects.create(
            user=self.user, product=self._create_product(), quantity=1,
        )

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_external_next_url_does_not_redirect(self, _mock_turnstile):
        response = self._login('https://evil.com/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_protocol_relative_next_url_does_not_redirect(self, _mock_turnstile):
        response = self._login('//evil.com/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_internal_next_url_is_allowed(self, _mock_turnstile):
        response = self._login('/orders/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/orders/')

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_no_next_redirects_to_home_when_cart_is_empty(self, _mock_turnstile):
        response = self._login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('home'))

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_no_next_redirects_to_cart_when_cart_has_items(self, _mock_turnstile):
        self._add_item_to_user_cart()
        response = self._login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_guest_cart_items_redirect_to_cart_after_login(self, _mock_turnstile):
        # Establish a guest session, then build a session cart for it.
        self.client.get(reverse('home'))
        guest_cart = Cart.objects.create(
            cart_id=self.client.session.session_key,
        )
        product = self._create_product()
        CartItem.objects.create(cart=guest_cart, product=product, quantity=2)

        response = self._login()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))
        self.assertTrue(
            CartItem.objects.filter(user=self.user, product=product).exists()
        )
