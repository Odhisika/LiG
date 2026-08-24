class PricePilotError(Exception):
    """Base class for all domain-level errors in PricePilot.

    Service-layer code should raise these (never bare Exception) so
    that API views can map them to consistent, documented HTTP
    responses via the exception handler below.
    """

    default_message = "An unexpected error occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(PricePilotError):
    default_message = "The requested resource was not found."


class ValidationError(PricePilotError):
    default_message = "Invalid input."


class PermissionDeniedError(PricePilotError):
    default_message = "You do not have permission to perform this action."


class ScraperError(PricePilotError):
    """Raised when a scraper fails to extract product data."""

    default_message = "Failed to scrape product data."


class ProductNotFoundOnSupplier(ScraperError):
    """Raised when a product URL returns 404 / not-found on the supplier.

    Distinct from transient ScraperErrors so the scheduler can mark the
    product out-of-stock instead of scrape_failed, and so the discovery
    scan can detect supplier-side removals.
    """

    default_message = "Product not found on supplier."


class ExternalServiceError(PricePilotError):
    """Raised when a downstream integration (email, Slack, store API) fails."""

    default_message = "An external service call failed."
