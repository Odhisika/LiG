from django.contrib import admin
from .models import (
    Product, ComputerProduct, SoftwareProduct, PeripheralProduct, 
    ReviewRating, ProductGallery, Brand, ProductSpecification,
    ProductVariant, ProductTag, ProductTagRelation, ReviewHelpful
)


# Inline Classes
class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 1
    fields = ('image', 'alt_text', 'image_type', 'order', 'is_active')


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    fields = ('name', 'value', 'group', 'order')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'price', 'compare_price', 'stock', 'attributes', 'is_active')
    readonly_fields = ('sku',)


class ReviewRatingInline(admin.TabularInline):
    model = ReviewRating
    extra = 0
    fields = ('user', 'rating', 'subject', 'status')
    readonly_fields = ('user', 'rating', 'subject', 'created_at')


# Base Product Admin
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 'sku', 'category', 'price', 'stock', 
        'is_available', 'is_featured', 'created_date'
    ]
    list_filter = [
        'category', 'is_available', 'is_featured', 'is_digital', 
        'requires_shipping', 'created_date'
    ]
    search_fields = ['product_name', 'sku', 'description', 'tags']
    prepopulated_fields = {'slug': ('product_name',)}
    list_editable = ['price', 'stock', 'is_available', 'is_featured']
    list_per_page = 25
    ordering = ['-created_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'slug', 'description', 'short_description', 'category')
        }),
        ('Pricing & Inventory', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('sku', 'barcode'),
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital')
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Physical Properties', {
            'fields': (
                'weight',
                ('dimensions_length', 'dimensions_width', 'dimensions_height')
            ),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('images',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


# Computer Product Admin
class ComputerProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 'brand', 'computer_type', 'price', 'stock',
        'get_processor_info', 'get_ram_info', 'get_storage_info',
        'screen_size', 'is_available', 'created_date'
    ]
    list_filter = [
        'brand', 'computer_type', 'processor_brand', 'operating_system',
        'is_available', 'is_featured', 'created_date'
    ]
    search_fields = [
        'product_name', 'brand__name', 'model_number', 'processor_model',
        'sku', 'description'
    ]
    prepopulated_fields = {'slug': ('product_name',)}
    list_editable = ['price', 'stock', 'is_available']
    list_per_page = 25
    ordering = ['-created_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'product_name', 'slug', 'description', 'short_description',
                'category', 'brand', 'model_number', 'computer_type'
            )
        }),
        ('Pricing & Inventory', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('sku', 'barcode'),
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Processor Specifications', {
            'fields': (
                ('processor_brand', 'processor_model'),
                ('processor_generation', 'processor_cores'),
                'processor_speed'
            )
        }),
        ('Memory & Storage', {
            'fields': (
                ('ram_size', 'ram_type'),
                ('ram_expandable', 'max_ram'),
                ('storage_capacity', 'storage_type'),
                'additional_storage_slots'
            )
        }),
        ('Graphics', {
            'fields': (
                ('gpu_brand', 'gpu_model'),
                'gpu_memory'
            )
        }),
        ('Display', {
            'fields': (
                ('screen_size', 'screen_resolution'),
                ('screen_type', 'refresh_rate'),
                'touchscreen'
            )
        }),
        ('System & Features', {
            'fields': (
                'operating_system',
                ('wifi_standard', 'bluetooth_version'),
                ('webcam', 'fingerprint_reader', 'backlit_keyboard')
            )
        }),
        ('Physical Properties', {
            'fields': (
                ('battery_life', 'color'),
                'weight',
                ('dimensions_length', 'dimensions_width', 'dimensions_height')
            ),
            'classes': ('collapse',)
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital')
            )
        }),
        ('SEO & Other', {
            'fields': (
                'meta_title', 'meta_description', 'tags',
                'warranty_period'
            ),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('images',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductVariantInline]
    
    def get_processor_info(self, obj):
        if obj.processor_brand and obj.processor_model:
            return f"{obj.processor_brand} {obj.processor_model}"
        return obj.processor_brand or obj.processor_model or '-'
    get_processor_info.short_description = 'Processor'
    
    def get_ram_info(self, obj):
        if obj.ram_size and obj.ram_type:
            return f"{obj.ram_size}GB {obj.ram_type}"
        return f"{obj.ram_size}GB" if obj.ram_size else '-'
    get_ram_info.short_description = 'RAM'
    
    def get_storage_info(self, obj):
        if obj.storage_capacity and obj.storage_type:
            return f"{obj.storage_capacity}GB {obj.storage_type}"
        return f"{obj.storage_capacity}GB" if obj.storage_capacity else '-'
    get_storage_info.short_description = 'Storage'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('brand', 'computer_type', 'category')


# Software Product Admin
class SoftwareProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 'software_type', 'version', 'license_type',
        'get_platform_info', 'price', 'stock', 'is_available', 'created_date'
    ]
    list_filter = [
        'software_type', 'license_type', 'is_available', 'is_featured',
        'is_digital', 'created_date'
    ]
    search_fields = [
        'product_name', 'software_type', 'version', 'developer',
        'publisher', 'sku', 'description'
    ]
    prepopulated_fields = {'slug': ('product_name',)}
    list_editable = ['price', 'stock', 'is_available']
    list_per_page = 25
    ordering = ['-created_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'product_name', 'slug', 'description', 'short_description',
                'category'
            )
        }),
        ('Software Details', {
            'fields': (
                ('software_type', 'version'),
                ('developer', 'publisher'),
                'license_type', 'platforms',
                'system_requirements'
            )
        }),
        ('Pricing & Inventory', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('sku', 'barcode'),
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Digital Delivery', {
            'fields': (
                'download_link', 'license_key', 'installation_guide'
            )
        }),
        ('Subscription Details', {
            'fields': (
                ('subscription_duration', 'max_devices')
            ),
            'classes': ('collapse',)
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital')
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('images',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline]
    
    def get_platform_info(self, obj):
        return obj.platforms[:50] + '...' if len(obj.platforms) > 50 else obj.platforms
    get_platform_info.short_description = 'Platforms'


# Peripheral Product Admin
class PeripheralProductAdmin(admin.ModelAdmin):
    list_display = [
        'product_name', 'brand', 'connectivity', 'get_compatibility_info',
        'get_warranty_info', 'price', 'stock', 'is_available', 'created_date'
    ]
    list_filter = [
        'brand', 'connectivity', 'battery_required', 'is_available',
        'is_featured', 'created_date'
    ]
    search_fields = [
        'product_name', 'brand__name', 'model_number', 'compatibility',
        'sku', 'description'
    ]
    prepopulated_fields = {'slug': ('product_name',)}
    list_editable = ['price', 'stock', 'is_available']
    list_per_page = 25
    ordering = ['-created_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'product_name', 'slug', 'description', 'short_description',
                'category', 'brand', 'model_number'
            )
        }),
        ('Connection & Compatibility', {
            'fields': ('connectivity', 'compatibility')
        }),
        ('Pricing & Inventory', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('sku', 'barcode'),
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Physical Properties', {
            'fields': (
                ('color', 'material'),
                'weight',
                ('dimensions_length', 'dimensions_width', 'dimensions_height')
            ),
            'classes': ('collapse',)
        }),
        ('Power & Battery', {
            'fields': (
                'battery_required',
                ('battery_type', 'battery_life'),
                'power_consumption'
            ),
            'classes': ('collapse',)
        }),
        ('Warranty', {
            'fields': (
                ('warranty_period', 'warranty_type')
            )
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital')
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('images',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline]
    
    def get_compatibility_info(self, obj):
        return (obj.compatibility[:50] + '...') if len(obj.compatibility) > 50 else obj.compatibility
    get_compatibility_info.short_description = 'Compatibility'
    
    def get_warranty_info(self, obj):
        return obj.warranty_period if obj.warranty_period else '-'
    get_warranty_info.short_description = 'Warranty'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('brand', 'category')


# Brand Admin
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'website']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Media & Links', {
            'fields': ('logo', 'website')
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


# Review Rating Admin
class ReviewRatingAdmin(admin.ModelAdmin):
    list_display = [
        'product', 'user', 'rating', 'subject', 'verified_purchase',
        'helpful_count', 'status', 'created_at'
    ]
    list_filter = [
        'rating', 'status', 'verified_purchase', 'created_at'
    ]
    search_fields = [
        'subject', 'review', 'product__product_name', 'user__username'
    ]
    list_editable = ['status']
    readonly_fields = ('created_at', 'updated_at', 'ip', 'user_agent')
    list_per_page = 25
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'user', 'subject', 'review', 'rating')
        }),
        ('Status & Verification', {
            'fields': (
                ('status', 'verified_purchase'),
                ('helpful_count', 'moderated_by')
            )
        }),
        ('Metadata', {
            'fields': ('ip', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product', 'user')


# Product Gallery Admin
class ProductGalleryAdmin(admin.ModelAdmin):
    list_display = ['product', 'image_type', 'alt_text', 'order', 'is_active']
    list_filter = ['image_type', 'is_active']
    search_fields = ['product__product_name', 'alt_text']
    list_editable = ['order', 'is_active']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


# Product Specification Admin
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'value', 'group', 'order']
    list_filter = ['group']
    search_fields = ['product__product_name', 'name', 'value']
    list_editable = ['order']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


# Product Variant Admin
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'sku', 'get_attributes', 'price', 'stock', 'is_active']
    list_filter = ['is_active']
    search_fields = ['product__product_name', 'sku']
    list_editable = ['price', 'stock', 'is_active']
    
    def get_attributes(self, obj):
        return ', '.join([f"{k}: {v}" for k, v in obj.attributes.items()])
    get_attributes.short_description = 'Attributes'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


# Product Tag Admin
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


# Review Helpful Admin
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'is_helpful', 'created_at']
    list_filter = ['is_helpful', 'created_at']
    readonly_fields = ('created_at',)


# Register all models
admin.site.register(Product, ProductAdmin)
admin.site.register(ComputerProduct, ComputerProductAdmin)
admin.site.register(SoftwareProduct, SoftwareProductAdmin)
admin.site.register(PeripheralProduct, PeripheralProductAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(ReviewRating, ReviewRatingAdmin)
admin.site.register(ProductGallery, ProductGalleryAdmin)
admin.site.register(ProductSpecification, ProductSpecificationAdmin)
admin.site.register(ProductVariant, ProductVariantAdmin)
admin.site.register(ProductTag, ProductTagAdmin)
admin.site.register(ReviewHelpful, ReviewHelpfulAdmin)

# Customize admin site
admin.site.site_header = "LiG Store Administration"
admin.site.site_title = "LiG Store Admin"
admin.site.index_title = "Welcome to LiG Store Administration"

