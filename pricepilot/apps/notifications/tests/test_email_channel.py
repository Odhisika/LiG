from apps.notifications.channels.email import EmailChannel
from apps.notifications.types import DigestSummary


class TestSubjectLine:
    def test_includes_all_nonzero_counts(self):
        channel = EmailChannel()
        summary = DigestSummary(products_updated=3, out_of_stock=1)

        subject = channel._subject(summary)

        assert "3 updated" in subject
        assert "1 out of stock" in subject

    def test_omits_zero_counts(self):
        channel = EmailChannel()
        summary = DigestSummary(products_updated=3)

        subject = channel._subject(summary)

        assert "out of stock" not in subject
        assert "scrape failure" not in subject

    def test_empty_summary_has_fallback_subject(self):
        channel = EmailChannel()
        subject = channel._subject(DigestSummary())
        assert subject == "PricePilot digest"


class TestBody:
    def test_includes_all_counts_even_zero(self):
        channel = EmailChannel()
        summary = DigestSummary(products_updated=2)

        body = channel._body(summary)

        assert "Products updated: 2" in body
        assert "Out of stock: 0" in body

    def test_includes_product_names_when_present(self):
        channel = EmailChannel()
        summary = DigestSummary(products_updated=1, product_names=["Widget A", "Widget B"])

        body = channel._body(summary)

        assert "Widget A" in body
        assert "Widget B" in body

    def test_omits_product_section_when_no_names(self):
        channel = EmailChannel()
        summary = DigestSummary(products_updated=1)

        body = channel._body(summary)

        assert "Affected products" not in body
