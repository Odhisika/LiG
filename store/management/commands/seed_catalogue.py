"""
Management command to seed the database with standard brands, categories,
computer types, and software types.

Run with:
    python3 manage.py seed_catalogue
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from category.models import Category, ComputerTypes, SoftwareTypes
from store.models import Brand


class Command(BaseCommand):
    help = 'Seeds the database with standard Brands, Categories, Computer Types, and Software Types.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing catalogue data before seeding (use with caution).',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing catalogue data...'))
            Brand.objects.all().delete()
            ComputerTypes.objects.all().delete()
            SoftwareTypes.objects.all().delete()
            Category.objects.all().delete()

        self.stdout.write(self.style.MIGRATE_HEADING('\n── Seeding Categories ──'))
        self._seed_categories()

        self.stdout.write(self.style.MIGRATE_HEADING('\n── Seeding Computer Types ──'))
        self._seed_computer_types()

        self.stdout.write(self.style.MIGRATE_HEADING('\n── Seeding Software Types ──'))
        self._seed_software_types()

        self.stdout.write(self.style.MIGRATE_HEADING('\n── Seeding Brands ──'))
        self._seed_brands()

        self.stdout.write(self.style.SUCCESS('\n✅ Catalogue seeding complete!\n'))

    # ─────────────────────────────────────────────────────────────────
    # CATEGORIES
    # ─────────────────────────────────────────────────────────────────
    def _seed_categories(self):
        categories = [
            {'name': 'Computers',          'sort_order': 1,  'featured': True},
            {'name': 'Software',           'sort_order': 2,  'featured': True},
            {'name': 'Networking',         'sort_order': 3,  'featured': True},
            {'name': 'Security & CCTV',    'sort_order': 4,  'featured': True},
            {'name': 'Peripherals',        'sort_order': 5,  'featured': False},
            {'name': 'Accessories',        'sort_order': 6,  'featured': False},
        ]
        for cat in categories:
            obj, created = Category.objects.get_or_create(
                slug=slugify(cat['name']),
                defaults={
                    'category_name': cat['name'],
                    'is_active': True,
                    'is_featured': cat['featured'],
                    'sort_order': cat['sort_order'],
                }
            )
            status = self.style.SUCCESS('created') if created else self.style.WARNING('already exists')
            self.stdout.write(f'  Category: {obj.category_name}  [{status}]')

    # ─────────────────────────────────────────────────────────────────
    # COMPUTER TYPES  (parent → children hierarchy)
    # ─────────────────────────────────────────────────────────────────
    def _seed_computer_types(self):
        # Top-level types first
        top_level = [
            {'name': 'Laptop',   'sort_order': 1},
            {'name': 'Desktop',  'sort_order': 2},
            {'name': 'Server',   'sort_order': 3},
        ]
        parents = {}
        for item in top_level:
            obj, created = ComputerTypes.objects.get_or_create(
                slug=slugify(item['name']),
                defaults={
                    'computer_type': item['name'],
                    'is_active': True,
                    'sort_order': item['sort_order'],
                    'parent': None,
                }
            )
            parents[item['name']] = obj
            status = self.style.SUCCESS('created') if created else self.style.WARNING('already exists')
            self.stdout.write(f'  [Top-Level]  {obj.computer_type}  [{status}]')

        # Child types (sub-categories)
        children = [
            # Laptop children
            {'name': 'Fresh Laptop',             'parent': 'Laptop',  'sort_order': 1},
            {'name': 'Slightly Used Laptop',     'parent': 'Laptop',  'sort_order': 2},
            {'name': 'Gaming Laptop',            'parent': 'Laptop',  'sort_order': 3},
            {'name': 'Business Laptop',          'parent': 'Laptop',  'sort_order': 4},
            {'name': '2-in-1 Laptop',            'parent': 'Laptop',  'sort_order': 5},
            # Desktop children
            {'name': 'Fresh Desktop',            'parent': 'Desktop', 'sort_order': 1},
            {'name': 'Slightly Used Desktop',    'parent': 'Desktop', 'sort_order': 2},
            {'name': 'Gaming Desktop',           'parent': 'Desktop', 'sort_order': 3},
            {'name': 'All-in-One Desktop',       'parent': 'Desktop', 'sort_order': 4},
            {'name': 'Mini PC',                  'parent': 'Desktop', 'sort_order': 5},
            # Server children
            {'name': 'Tower Server',             'parent': 'Server',  'sort_order': 1},
            {'name': 'Rack Server',              'parent': 'Server',  'sort_order': 2},
            {'name': 'NAS Storage Server',       'parent': 'Server',  'sort_order': 3},
        ]
        for child in children:
            parent_obj = parents.get(child['parent'])
            obj, created = ComputerTypes.objects.get_or_create(
                slug=slugify(child['name']),
                defaults={
                    'computer_type': child['name'],
                    'is_active': True,
                    'sort_order': child['sort_order'],
                    'parent': parent_obj,
                }
            )
            status = self.style.SUCCESS('created') if created else self.style.WARNING('already exists')
            self.stdout.write(f'    ↳ [{child["parent"]}]  {obj.computer_type}  [{status}]')

    # ─────────────────────────────────────────────────────────────────
    # SOFTWARE TYPES
    # ─────────────────────────────────────────────────────────────────
    def _seed_software_types(self):
        software_types = [
            {'name': 'Antivirus & Security',     'sort_order': 1},
            {'name': 'Office Suite',             'sort_order': 2},
            {'name': 'Operating System',         'sort_order': 3},
            {'name': 'Design & Creative',        'sort_order': 4},
            {'name': 'Accounting & Finance',     'sort_order': 5},
            {'name': 'Development Tools',        'sort_order': 6},
            {'name': 'Database Software',        'sort_order': 7},
            {'name': 'Video Editing',            'sort_order': 8},
            {'name': 'Remote Desktop & VPN',     'sort_order': 9},
            {'name': 'Backup & Recovery',        'sort_order': 10},
            {'name': 'Network Management',       'sort_order': 11},
            {'name': 'Point of Sale (POS)',      'sort_order': 12},
        ]
        for item in software_types:
            obj, created = SoftwareTypes.objects.get_or_create(
                slug=slugify(item['name']),
                defaults={
                    'software_type': item['name'],
                    'is_active': True,
                    'sort_order': item['sort_order'],
                }
            )
            status = self.style.SUCCESS('created') if created else self.style.WARNING('already exists')
            self.stdout.write(f'  Software Type: {obj.software_type}  [{status}]')

    # ─────────────────────────────────────────────────────────────────
    # BRANDS  (grouped by product category)
    # ─────────────────────────────────────────────────────────────────
    def _seed_brands(self):
        # c=computers, n=networking, s=security, p=peripherals, sw=software
        brands = [
            # ── Laptop / Desktop Brands ──────────────────────────────────────
            {'name': 'Dell',            'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.dell.com'},
            {'name': 'HP',              'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.hp.com'},
            {'name': 'Lenovo',          'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.lenovo.com'},
            {'name': 'Apple',           'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.apple.com'},
            {'name': 'Asus',            'c': True,  'n': True,  's': False, 'p': True,  'sw': False, 'website': 'https://www.asus.com'},
            {'name': 'Acer',            'c': True,  'n': False, 's': False, 'p': False, 'sw': False, 'website': 'https://www.acer.com'},
            {'name': 'MSI',             'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.msi.com'},
            {'name': 'Samsung',         'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.samsung.com'},
            {'name': 'Toshiba',         'c': True,  'n': False, 's': False, 'p': False, 'sw': False, 'website': 'https://www.toshiba.com'},
            {'name': 'Microsoft',       'c': True,  'n': False, 's': False, 'p': True,  'sw': True,  'website': 'https://www.microsoft.com'},
            {'name': 'Razer',           'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.razer.com'},
            {'name': 'Huawei',          'c': True,  'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.huawei.com'},
            {'name': 'LG',              'c': True,  'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.lg.com'},

            # ── Networking Brands ─────────────────────────────────────────────
            {'name': 'Cisco',           'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.cisco.com'},
            {'name': 'TP-Link',         'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.tp-link.com'},
            {'name': 'MikroTik',        'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.mikrotik.com'},
            {'name': 'Ubiquiti',        'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.ui.com'},
            {'name': 'Netgear',         'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.netgear.com'},
            {'name': 'D-Link',          'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.dlink.com'},
            {'name': 'Zyxel',           'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.zyxel.com'},
            {'name': 'Aruba',           'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.arubanetworks.com'},
            {'name': 'Juniper',         'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.juniper.net'},
            {'name': 'Fortinet',        'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.fortinet.com'},
            {'name': 'Tenda',           'c': False, 'n': True,  's': False, 'p': False, 'sw': False, 'website': 'https://www.tendacn.com'},

            # ── Security / CCTV Brands ────────────────────────────────────────
            {'name': 'Hikvision',       'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://www.hikvision.com'},
            {'name': 'Dahua',           'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://www.dahuasecurity.com'},
            {'name': 'Reolink',         'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://reolink.com'},
            {'name': 'Axis',            'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://www.axis.com'},
            {'name': 'Hanwha',          'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://www.hanwhavision.com'},
            {'name': 'Bosch Security',  'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://www.boschsecurity.com'},
            {'name': 'Uniview (UNV)',   'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://www.uniview.com'},
            {'name': 'Amcrest',         'c': False, 'n': False, 's': True,  'p': False, 'sw': False, 'website': 'https://amcrest.com'},

            # ── Peripherals & Accessories ─────────────────────────────────────
            {'name': 'Logitech',        'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.logitech.com'},
            {'name': 'Corsair',         'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.corsair.com'},
            {'name': 'SteelSeries',     'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.steelseries.com'},
            {'name': 'Kingston',        'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.kingston.com'},
            {'name': 'Seagate',         'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.seagate.com'},
            {'name': 'Western Digital', 'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.westerndigital.com'},
            {'name': 'Crucial',         'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.crucial.com'},
            {'name': 'Belkin',          'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.belkin.com'},
            {'name': 'Epson',           'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.epson.com'},
            {'name': 'Canon',           'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.canon.com'},
            {'name': 'Brother',         'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.brother.com'},
            {'name': 'Philips',         'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.philips.com'},
            {'name': 'BenQ',            'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.benq.com'},
            {'name': 'AOC',             'c': False, 'n': False, 's': False, 'p': True,  'sw': False, 'website': 'https://www.aoc.com'},

            # ── Generic ───────────────────────────────────────────────────────
            {'name': 'Generic',         'c': True,  'n': True,  's': True,  'p': True,  'sw': True,  'website': ''},
        ]

        for item in brands:
            obj, created = Brand.objects.get_or_create(
                slug=slugify(item['name']),
                defaults={
                    'name': item['name'],
                    'website': item.get('website', ''),
                    'is_active': True,
                    'for_computers':   item.get('c', False),
                    'for_networking':  item.get('n', False),
                    'for_security':    item.get('s', False),
                    'for_peripherals': item.get('p', False),
                    'for_software':    item.get('sw', False),
                }
            )
            # Always update flags on existing brands
            if not created:
                obj.for_computers   = item.get('c', False)
                obj.for_networking  = item.get('n', False)
                obj.for_security    = item.get('s', False)
                obj.for_peripherals = item.get('p', False)
                obj.for_software    = item.get('sw', False)
                obj.save(update_fields=['for_computers', 'for_networking', 'for_security', 'for_peripherals', 'for_software'])
            status = self.style.SUCCESS('created') if created else self.style.WARNING('updated flags')
            self.stdout.write(f'  Brand: {obj.name}  [{status}]')
