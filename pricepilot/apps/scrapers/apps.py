from django.apps import AppConfig


class ScrapersConfig(AppConfig):
    name = "apps.scrapers"

    def ready(self):
        # Importing each scraper module triggers its @ScraperRegistry.register
        # decorator. New scrapers must be imported here to be discoverable.
        from apps.scrapers import catlog  # noqa: F401
