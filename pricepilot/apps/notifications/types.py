from dataclasses import dataclass, field


@dataclass
class DigestSummary:
    """Aggregated counts for one owner's pending events, batched into a
    single message rather than one per event.
    """

    products_updated: int = 0
    out_of_stock: int = 0
    low_stock: int = 0
    scrape_failed: int = 0
    supplier_unavailable: int = 0
    new_products_found: int = 0
    # A capped sample of affected product names for the message body —
    # not exhaustive, just enough to be useful without an unbounded email.
    product_names: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            self.products_updated
            + self.out_of_stock
            + self.low_stock
            + self.scrape_failed
            + self.supplier_unavailable
            + self.new_products_found
        )

    @property
    def is_empty(self) -> bool:
        return self.total == 0
