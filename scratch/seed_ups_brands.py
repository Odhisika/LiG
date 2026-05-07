import os
import sys
import django

# Add the project root to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LiG.settings')
django.setup()

from store.models import Brand
from django.utils.text import slugify

def seed_ups_brands():
    ups_brands = [
        {'name': 'APC', 'description': 'American Power Conversion - global leader in UPS systems.'},
        {'name': 'CyberPower', 'description': 'Professional-grade power protection solutions.'},
        {'name': 'Eaton', 'description': 'Intelligent power management for enterprise and home.'},
        {'name': 'Tripp Lite', 'description': 'Reliable power protection and connectivity solutions.'},
        {'name': 'Vertiv', 'description': 'Critical digital infrastructure and continuity solutions.'},
        {'name': 'Mercury', 'description': 'Popular power protection brand in West Africa.'},
        {'name': 'Bluegate', 'description': 'Reliable UPS and power backup brand.'},
    ]

    for brand_data in ups_brands:
        brand, created = Brand.objects.get_or_create(
            name=brand_data['name'],
            defaults={
                'description': brand_data['description'],
                'slug': slugify(brand_data['name']),
                'for_ups': True,
                'is_active': True
            }
        )
        if not created:
            brand.for_ups = True
            brand.save()
            print(f"Updated existing brand: {brand.name}")
        else:
            print(f"Created new brand: {brand.name}")

if __name__ == '__main__':
    seed_ups_brands()
