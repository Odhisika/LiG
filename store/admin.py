from django.contrib import admin
from .models import Product, ComputerProduct, SoftwareProduct, PeripheralProduct, ReviewRating, ProductGallery
import admin_thumbnails

@admin_thumbnails.thumbnail('image')
class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1

@admin.register(Product)
class BaseProductAdmin(admin.ModelAdmin):
    
    list_display = ('product_name', 'price', 'stock', 'category', 'modified_date', 'is_available')
    prepopulated_fields = {'slug': ('product_name',)}
    inlines = [ProductGalleryInline]
    list_filter = ('category', 'is_available', 'modified_date')
    search_fields = ('product_name', 'category__name')

@admin.register(ComputerProduct)
class ComputerProductAdmin(BaseProductAdmin):
   
    list_display = BaseProductAdmin.list_display + ('brand', 'processor', 'ram', 'storage', 'gpu', 'screen_size', 'operating_system')

@admin.register(SoftwareProduct)
class SoftwareProductAdmin(BaseProductAdmin):
    
    list_display = BaseProductAdmin.list_display + ('software_type', 'version', 'license_type', 'platform')

@admin.register(PeripheralProduct)
class PeripheralProductAdmin(BaseProductAdmin):

    list_display = BaseProductAdmin.list_display + ('brand', 'connectivity', 'compatibility', 'warranty')

# Registering Other Models
admin.site.register(ReviewRating)
admin.site.register(ProductGallery)
