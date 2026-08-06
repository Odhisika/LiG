import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from django.core import mail

from accounts.models import Account
from orders.models import Order

from .models import Payment


class HubtelWebhookTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = Account.objects.create_user(
            first_name='Test', last_name='User', username='testuser',
            email='test@example.com', password='secret123',
        )
        self.user.is_active = True
        self.user.save()
        self.order = Order.objects.create(
            user=self.user,
            order_number=f'ORD-{uuid.uuid4().hex[:8]}',
            first_name='Test', last_name='User',
            phone='0240000000', email='test@example.com',
            address_line_1='1 Test St', country='GH', state='GA', city='Accra',
            order_total=Decimal('100.00'), tax=Decimal('0.00'),
            status='Pending', is_ordered=True,
        )
        self.payment = Payment.objects.create(
            user=self.user, order=self.order, amount=Decimal('100.00'),
            email='test@example.com', status='pending', gateway='hubtel',
        )

    def _post_webhook(self, status='Success', ref=None):
        payload = {
            'Status': status,
            'ClientReference': ref or self.payment.ref,
            'TransactionId': 'HUBTEL-123',
        }
        return self.client.post(
            reverse('hubtel_webhook'),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def _hubtel_pending(self, instance):
        instance.verify_transaction.return_value = (False, {'status': 'pending'})

    def _hubtel_success(self, instance):
        instance.verify_transaction.return_value = (True, {
            'status': 'success',
            'amount': 100.0,
            'channel': 'mobile_money',
            'currency': 'GHS',
            'transaction_id': 'HUBTEL-123',
            'reference': self.payment.ref,
            'paid_at': '',
        })

    @patch('payment.models.Hubtel')
    def test_forged_success_claim_does_not_mark_paid(self, MockHubtel):
        self._hubtel_pending(MockHubtel.return_value)

        response = self._post_webhook('Success')
        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertFalse(self.payment.verified)
        self.assertEqual(self.payment.status, 'pending')
        self.assertFalse(self.order.paid)
        self.assertEqual(self.order.status, 'Pending')
        MockHubtel.return_value.verify_transaction.assert_called_once()

    @patch('payment.models.Hubtel')
    def test_success_only_when_hubtel_api_confirms(self, MockHubtel):
        self._hubtel_success(MockHubtel.return_value)

        response = self._post_webhook('Success')
        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertTrue(self.payment.verified)
        self.assertEqual(self.payment.status, 'successful')
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.status, 'Pending')

    @patch('payment.models.Hubtel')
    def test_success_sends_payment_confirmation_email(self, MockHubtel):
        self._hubtel_success(MockHubtel.return_value)

        response = self._post_webhook('Success')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Confirmed', mail.outbox[0].subject)
        self.assertIn(self.user.email, mail.outbox[0].to)

    @patch('payment.models.Hubtel')
    def test_forged_failure_claim_does_not_mark_failed(self, MockHubtel):
        self._hubtel_pending(MockHubtel.return_value)

        response = self._post_webhook('Failed')
        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertNotEqual(self.payment.status, 'failed')
        self.assertEqual(self.payment.status, 'pending')

    @patch('payment.models.Hubtel')
    def test_non_hubtel_payment_ignored(self, MockHubtel):
        self.payment.gateway = 'paystack'
        self.payment.save()

        response = self._post_webhook('Success')
        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertFalse(self.payment.verified)
        MockHubtel.return_value.verify_transaction.assert_not_called()

    @patch('payment.models.Hubtel')
    def test_unknown_reference_ignored(self, MockHubtel):
        response = self._post_webhook('Success', ref='PAY_NOTREAL')
        self.assertEqual(response.status_code, 200)

        self.payment.refresh_from_db()
        self.assertFalse(self.payment.verified)
        MockHubtel.return_value.verify_transaction.assert_not_called()


class PaymentAccessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = Account.objects.create_user(
            first_name='Owner', last_name='User', username='owner',
            email='owner@example.com', password='secret123',
        )
        self.owner.is_active = True
        self.owner.save()
        self.attacker = Account.objects.create_user(
            first_name='Attacker', last_name='User', username='attacker',
            email='attacker@example.com', password='secret123',
        )
        self.attacker.is_active = True
        self.attacker.save()
        self.order = Order.objects.create(
            user=self.owner,
            order_number='20260806001',
            first_name='Owner', last_name='User',
            phone='0240000000', email='owner@example.com',
            address_line_1='1 Test St', country='GH', state='GA', city='Accra',
            order_total=Decimal('100.00'), tax=Decimal('0.00'),
            status='Pending', is_ordered=True,
        )
        self.payment = Payment.objects.create(
            user=self.owner, order=self.order, amount=Decimal('100.00'),
            email='owner@example.com', status='pending', gateway='hubtel',
        )
        self.status_url = reverse('payment_status', kwargs={'payment_id': self.payment.id})
        self.detail_url = reverse('payment_detail', kwargs={'payment_id': self.payment.id})

    def test_status_allowed_for_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ref'], self.payment.ref)

    def test_status_denied_for_other_user(self):
        self.client.force_login(self.attacker)
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Permission denied')

    def test_status_denied_for_anonymous(self):
        response = self.client.get(self.status_url)
        self.assertEqual(response.status_code, 403)

    def test_detail_allowed_for_owner(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)

    def test_detail_denied_for_other_user(self):
        self.client.force_login(self.attacker)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))

    def test_detail_denied_for_anonymous(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart'))
