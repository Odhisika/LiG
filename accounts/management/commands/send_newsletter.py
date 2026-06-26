import json
import os
from django.core.management.base import BaseCommand, CommandError
from accounts.models import NewsletterSubscriber
from accounts.utils.email import send_html_email
from store.models import Product


class Command(BaseCommand):
    help = 'Send a newsletter/promotional email to all active subscribers'

    def add_arguments(self, parser):
        parser.add_argument('subject', type=str, help='Email subject')
        parser.add_argument('body_file', type=str, help='Path to HTML body file')
        parser.add_argument('--button-text', type=str, default='', help='Call-to-action button text')
        parser.add_argument('--button-url', type=str, default='', help='Call-to-action button URL')
        parser.add_argument('--dry-run', action='store_true', help='Print recipient count without sending')
        parser.add_argument('--email', type=str, default='', help='Send to a single email address only')
        parser.add_argument('--products', type=str, default='', help='Comma-separated product IDs to feature')
        parser.add_argument('--site-url', type=str, default='https://lig.com.gh', help='Site base URL for product links')

    def handle(self, *args, **options):
        subject = options['subject']
        body_file = options['body_file']

        if not os.path.isfile(body_file):
            raise CommandError(f'Body file not found: {body_file}')

        with open(body_file, 'r') as f:
            body = f.read()

        if options['email']:
            subscribers = NewsletterSubscriber.objects.filter(email=options['email'], is_active=True)
        else:
            subscribers = NewsletterSubscriber.objects.filter(is_active=True)

        count = subscribers.count()
        if count == 0:
            self.stdout.write(self.style.WARNING('No active subscribers found.'))
            return

        featured_products = []
        if options['products']:
            ids = [int(i.strip()) for i in options['products'].split(',') if i.strip().isdigit()]
            featured_products = list(Product.objects.filter(id__in=ids, is_available=True))

        ctx = {
            'subject': subject,
            'body': body,
            'button_text': options.get('button_text', ''),
            'button_url': options.get('button_url', ''),
            'featured_products': featured_products,
            'site_url': options['site_url'],
        }

        if options['dry_run']:
            self.stdout.write(f'Would send to {count} subscriber(s). (dry run)')
            self.stdout.write(f'Featured products: {len(featured_products)}')
            return

        sent = 0
        failed = 0
        for sub in subscribers.iterator():
            try:
                send_html_email(subject, 'emails/promotion_email.html', ctx, [sub.email])
                sent += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to send to {sub.email}: {e}'))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'Done. Sent: {sent}, Failed: {failed}'))
