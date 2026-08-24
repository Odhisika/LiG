from unittest.mock import MagicMock, patch

import pytest
from django.core import mail

from apps.accounts.models import User
from apps.notifications.models import NotificationEvent
from apps.notifications.services import NotificationService
from apps.notifications.types import DigestSummary
from apps.products.models import Product
from apps.suppliers.models import Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(email="owner@example.com", password="supersecret123")


@pytest.fixture
def other_user():
    return User.objects.create_user(email="other@example.com", password="supersecret123")


@pytest.fixture
def supplier(user):
    return Supplier.objects.create(owner=user, name="AliExpress", website="https://aliexpress.com")


@pytest.fixture
def product(user, supplier):
    return Product.objects.create(
        owner=user,
        supplier=supplier,
        name="Widget",
        supplier_url="https://a.com",
        supplier_price=10,
    )


class TestRecordEvent:
    def test_creates_unsent_event(self, user, product):
        event = NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )

        assert event.sent is False
        assert event.owner == user
        assert event.product == product

    def test_payload_stored(self, user, product):
        event = NotificationService.record_event(
            user,
            NotificationEvent.EventType.PRODUCT_UPDATED,
            product=product,
            payload={"old_price": "10.00", "new_price": "12.00"},
        )

        assert event.payload == {"old_price": "10.00", "new_price": "12.00"}


class TestBuildSummary:
    def test_counts_by_event_type(self, user, product):
        events = [
            NotificationService.record_event(
                user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
            ),
            NotificationService.record_event(
                user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
            ),
            NotificationService.record_event(
                user, NotificationEvent.EventType.OUT_OF_STOCK, product=product
            ),
            NotificationService.record_event(
                user, NotificationEvent.EventType.SCRAPE_FAILED, product=product
            ),
        ]

        summary = NotificationService._build_summary(events)

        assert summary.products_updated == 2
        assert summary.out_of_stock == 1
        assert summary.scrape_failed == 1
        assert summary.supplier_unavailable == 0
        assert summary.total == 4

    def test_dedupes_product_names(self, user, product):
        events = [
            NotificationService.record_event(
                user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
            ),
            NotificationService.record_event(
                user, NotificationEvent.EventType.OUT_OF_STOCK, product=product
            ),
        ]

        summary = NotificationService._build_summary(events)

        assert summary.product_names == ["Widget"]


class TestSendPendingDigests:
    def test_sends_one_digest_per_owner_via_console_backend(self, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )
        NotificationService.record_event(
            user, NotificationEvent.EventType.OUT_OF_STOCK, product=product
        )

        sent_count = NotificationService.send_pending_digests()

        assert sent_count == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]

    def test_marks_events_sent(self, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )

        NotificationService.send_pending_digests()

        event = NotificationEvent.objects.get(owner=user)
        assert event.sent is True
        assert event.sent_at is not None

    def test_does_not_resend_already_sent_events(self, user, product):
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )
        NotificationService.send_pending_digests()

        second_run_count = NotificationService.send_pending_digests()

        assert second_run_count == 0
        assert len(mail.outbox) == 1  # still just the one email from the first run

    def test_batches_multiple_events_into_one_email(self, user, product):
        for _ in range(5):
            NotificationService.record_event(
                user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
            )

        sent_count = NotificationService.send_pending_digests()

        assert sent_count == 1
        assert len(mail.outbox) == 1  # one email, not five

    def test_separate_digest_per_owner(self, user, other_user, product):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        other_product = Product.objects.create(
            owner=other_user,
            supplier=other_supplier,
            name="Other Widget",
            supplier_url="https://b.com",
            supplier_price=5,
        )
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )
        NotificationService.record_event(
            other_user, NotificationEvent.EventType.PRODUCT_UPDATED, product=other_product
        )

        sent_count = NotificationService.send_pending_digests()

        assert sent_count == 2
        assert len(mail.outbox) == 2
        recipients = {msg.to[0] for msg in mail.outbox}
        assert recipients == {user.email, other_user.email}

    def test_no_pending_events_sends_nothing(self):
        sent_count = NotificationService.send_pending_digests()

        assert sent_count == 0
        assert len(mail.outbox) == 0

    def test_one_failed_send_does_not_block_others(self, user, other_user, product):
        other_supplier = Supplier.objects.create(
            owner=other_user, name="Theirs", website="https://theirs.com"
        )
        other_product = Product.objects.create(
            owner=other_user,
            supplier=other_supplier,
            name="Other Widget",
            supplier_url="https://b.com",
            supplier_price=5,
        )
        NotificationService.record_event(
            user, NotificationEvent.EventType.PRODUCT_UPDATED, product=product
        )
        NotificationService.record_event(
            other_user, NotificationEvent.EventType.PRODUCT_UPDATED, product=other_product
        )

        failing_channel = MagicMock()
        failing_channel.send_digest.side_effect = [Exception("SMTP down"), None]

        with patch(
            "apps.notifications.services.NotificationChannelRegistry.get",
            return_value=failing_channel,
        ):
            sent_count = NotificationService.send_pending_digests()

        # one succeeded, one failed — failure shouldn't block the other
        assert sent_count == 1
        assert failing_channel.send_digest.call_count == 2


class TestDigestSummary:
    def test_is_empty_true_when_no_counts(self):
        assert DigestSummary().is_empty is True

    def test_is_empty_false_when_any_count_present(self):
        assert DigestSummary(out_of_stock=1).is_empty is False
