from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ScrapedProduct:
    """What every scraper hands back, regardless of which site it scraped.

    The rest of the system (Price Monitor Engine, Sync Engine, History)
    only ever depends on this shape — never on a scraper's internals.
    Per the blueprint: "the rest of the system doesn't care where the
    data came from."
    """

    title: str
    price: Decimal
    currency: str
    stock: int | None  # None = availability unknown (not the same as 0)
    description: str = ""
    images: list[str] = field(default_factory=list)
