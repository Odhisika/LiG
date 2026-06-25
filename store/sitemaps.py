from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Category

class ProductSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return Product.objects.filter(is_available=True)

    def lastmod(self, obj):
        return obj.modified_date

    def location(self, obj):
        return obj.get_url()


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return obj.get_url()


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return [
            'home',
            'store',
            'computers_all',
            'laptops',
            'fresh_laptops',
            'used_laptops',
            'desktops',
            'fresh_desktops',
            'used_desktops',
            'all_in_one_computers',
            'peripherals',
            'networking_all',
            'switches',
            'routers-and-modems',
            'access-points',
            'ups',
            'security_cameras',
            'ip_cameras',
            'cctv_kits',
            'nvr_dvr',
            'software_all',
            'operatingSystems',
            'applications',
            'office_suite',
            'design_creative',
            'accounting_finance',
            'video_editing',
            'point_of_sale',
            'security_utilities',
            'antivirus_security',
            'remote_desktop_vpn',
            'backup_recovery',
            'network_management',
            'developmentTools',
            'development_tools_only',
            'database_software',
            'CCTVInstallation',
            'cctvServices',
            'hardwareRepairs',
            'hardwareServices',
            'networkingSolutions',
            'networkingServices',
            'research',
        ]

    def location(self, item):
        return reverse(item)
