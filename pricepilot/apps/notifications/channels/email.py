import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import User
from apps.notifications.channels.base import NotificationChannel
from apps.notifications.registry import NotificationChannelRegistry
from apps.notifications.types import DigestSummary

logger = logging.getLogger(__name__)


@NotificationChannelRegistry.register
class EmailChannel(NotificationChannel):
    key = "email"

    def send_digest(self, owner: User, summary: DigestSummary) -> None:
        send_mail(
            subject=self._subject(summary),
            message=self._body(summary),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=False,
        )
        logger.info("Sent notification digest to %s (%d events).", owner.email, summary.total)

    def _subject(self, summary: DigestSummary) -> str:
        parts = []
        if summary.products_updated:
            parts.append(f"{summary.products_updated} updated")
        if summary.low_stock:
            parts.append(f"{summary.low_stock} low stock")
        if summary.out_of_stock:
            parts.append(f"{summary.out_of_stock} out of stock")
        if summary.scrape_failed:
            parts.append(f"{summary.scrape_failed} scrape failure(s)")
        if summary.supplier_unavailable:
            parts.append(f"{summary.supplier_unavailable} supplier issue(s)")
        if summary.new_products_found:
            parts.append(f"{summary.new_products_found} new product(s) found")
        if not parts:
            return "PricePilot digest"
        return "PricePilot: " + ", ".join(parts)

    def _body(self, summary: DigestSummary) -> str:
        lines = [
            f"Products updated: {summary.products_updated}",
            f"Low stock: {summary.low_stock}",
            f"Out of stock: {summary.out_of_stock}",
            f"Scrape failures: {summary.scrape_failed}",
            f"Supplier issues: {summary.supplier_unavailable}",
            f"New products found: {summary.new_products_found}",
        ]
        if summary.product_names:
            lines.append("")
            lines.append("Affected products:")
            lines.extend(f"- {name}" for name in summary.product_names)
        return "\n".join(lines)
