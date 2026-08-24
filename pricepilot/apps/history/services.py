from apps.accounts.models import User
from apps.common.exceptions import NotFoundError
from apps.history.models import PriceHistory


class HistoryService:
    """Read-only access to PriceHistory. Nothing here writes — rows are
    created exclusively by PriceMonitorService (apps/products/services.py)
    at the moment a change is detected.
    """

    @staticmethod
    def list_for_owner(owner: User, *, product_id=None, date_from=None, date_to=None):
        qs = PriceHistory.objects.filter(owner=owner)
        if product_id:
            qs = qs.filter(product_id=product_id)
        if date_from:
            qs = qs.filter(created_at__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__lte=date_to)
        return qs

    @staticmethod
    def get_for_owner(owner: User, history_id) -> PriceHistory:
        entry = PriceHistory.objects.filter(owner=owner, id=history_id).first()
        if entry is None:
            raise NotFoundError("History entry not found.")
        return entry
