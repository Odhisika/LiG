from django.core.management.base import BaseCommand

from apps.sync.services import StoreSyncService, is_configured


class Command(BaseCommand):
    help = "Push PricePilot's monitored values into the merchant store (LiG)."

    def handle(self, *args, **options):
        if not is_configured():
            self.stdout.write(
                self.style.WARNING(
                    "Store sync is not configured. Set LIG_DATABASE_URL and "
                    "LIG_SYNC_ENABLED=True, then run migrations on both databases."
                )
            )
            return
        tally = StoreSyncService.sync_all()
        self.stdout.write(self.style.SUCCESS(f"Store sync finished: {tally}"))
