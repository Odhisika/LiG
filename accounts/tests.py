from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Account


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

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_external_next_url_does_not_redirect(self, _mock_turnstile):
        response = self._login('https://evil.com/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_protocol_relative_next_url_does_not_redirect(self, _mock_turnstile):
        response = self._login('//evil.com/phish')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_internal_next_url_is_allowed(self, _mock_turnstile):
        response = self._login('/orders/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/orders/')

    @patch('accounts.views.verify_turnstile', return_value=True)
    def test_no_next_redirects_to_cart(self, _mock_turnstile):
        response = self._login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))
