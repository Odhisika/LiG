from django.core.management.base import BaseCommand, CommandError

from apps.common.exceptions import ScraperError
from apps.scrapers.registry import ScraperRegistry


class Command(BaseCommand):
    """Run a registered scraper against a real URL and print what it found.

    Usage:
        python manage.py inspect_scrape <url> [--scraper catlog]

    Use this to validate/tune a scraper against a live page — this
    command needs real internet access, so run it inside Docker or
    your local environment, not in CI.
    """

    help = "Run a scraper against a real URL and print the extracted ScrapedProduct."

    def add_arguments(self, parser):
        parser.add_argument("url", type=str)
        parser.add_argument("--scraper", type=str, default="catlog")

    def handle(self, *args, **options):
        url = options["url"]
        scraper_key = options["scraper"]

        self.stdout.write(f"Scraper: {scraper_key}")
        self.stdout.write(f"URL:     {url}")
        self.stdout.write("Rendering page (this launches headless Chromium)...\n")

        try:
            scraper = ScraperRegistry.get(scraper_key)
            result = scraper.fetch(url)
        except ScraperError as exc:
            raise CommandError(f"Scrape failed: {exc.message}") from exc

        self.stdout.write(self.style.SUCCESS("Scrape succeeded:"))
        self.stdout.write(f"  title:       {result.title}")
        self.stdout.write(f"  price:       {result.price} {result.currency}")
        self.stdout.write(f"  stock:       {result.stock}")
        self.stdout.write(f"  images:      {result.images}")
        self.stdout.write(f"  description: {result.description[:120]}...")
