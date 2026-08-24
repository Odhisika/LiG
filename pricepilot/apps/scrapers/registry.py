from apps.common.exceptions import NotFoundError
from apps.scrapers.base import BaseScraper


class ScraperRegistry:
    """Maps a Supplier's `default_scraper` string to a concrete scraper
    class. This is the seam that keeps the rest of the system generic —
    adding a new supplier's scraper means registering it here, not
    touching Products, the Price Monitor Engine, or anything downstream.
    """

    _registry: dict[str, type[BaseScraper]] = {}

    @classmethod
    def register(cls, scraper_cls: type[BaseScraper]) -> type[BaseScraper]:
        """Use as a decorator: @ScraperRegistry.register on a BaseScraper subclass."""
        cls._registry[scraper_cls.key] = scraper_cls
        return scraper_cls

    @classmethod
    def get(cls, key: str) -> BaseScraper:
        scraper_cls = cls._registry.get(key)
        if scraper_cls is None:
            raise NotFoundError(f"No scraper registered for key '{key}'.")
        return scraper_cls()

    @classmethod
    def available_keys(cls) -> list[str]:
        return sorted(cls._registry.keys())
