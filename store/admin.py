from django.contrib import admin
from .models import (
    Product, ComputerProduct, SoftwareProduct, PeripheralProduct,
    ReviewRating, ProductGallery, Brand, ProductSpecification,
    ProductVariant, ProductTag, ProductTagRelation, ReviewHelpful,
    HomeBanner
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
    readonly_fields = ('user', 'subject', 'review', 'rating', 'ip', 'status', 'created_at', 'updated_at')
    can_delete = False
    fields = ('user', 'subject', 'rating', 'status', 'created_at')


class ProductTagRelationInline(admin.TabularInline):
    model = ProductTagRelation
    extra = 1
    fields = ('tag',)


# Admin Classes
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'is_available', 'created_date', 'modified_date', 'is_featured')
    list_editable = ('price', 'stock', 'is_available', 'is_featured')
    list_filter = ('is_available', 'is_featured', 'category', 'created_date')
    search_fields = ('product_name', 'slug', 'description')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductVariantInline, ProductTagRelationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'slug', 'category', 'brand', 'short_description')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Pricing', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('barcode',),
            )
        }),
        ('Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
                'condition'
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Physical Properties', {
            'fields': ('weight', 'dimensions_length', 'dimensions_width', 'dimensions_height'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('slug', 'created_date', 'modified_date')
        return ('created_date', 'modified_date')

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('product_name',)}


class ComputerProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'brand', 'condition', 'is_available')
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ['brand', 'condition', 'is_available', 'is_featured', 'created_date']
    search_fields = ('product_name', 'slug', 'description')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'slug', 'category', 'brand', 'short_description')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Pricing & Inventory', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('barcode',),
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
                'condition'
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Physical Properties', {
            'fields': ('weight', 'dimensions_length', 'dimensions_width', 'dimensions_height'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('slug', 'created_date', 'modified_date')
        return ('created_date', 'modified_date')

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('product_name',)}


class SoftwareProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'condition', 'is_available')
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ['condition', 'is_available', 'is_featured', 'created_date']
    search_fields = ('product_name', 'slug', 'description')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductTagRelationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'slug', 'category', 'short_description')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('stock', 'is_available'),
            )
        }),
        ('Software Details', {
            'fields': ('software_type', 'license_type', 'license_key', 'download_link'),
            'classes': ('collapse',)
        }),
        ('Product Status', {
            'fields': (
                ('is_featured', 'condition',)
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('slug', 'created_date', 'modified_date')
        return ('created_date', 'modified_date')

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('product_name',)}


class PeripheralProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'brand', 'condition', 'is_available')
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ['brand', 'condition', 'is_available', 'is_featured', 'created_date']
    search_fields = ('product_name', 'slug', 'description')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    fieldsets = (
        ('Basic Information', {
            'fields': ('product_name', 'slug', 'category', 'brand', 'short_description')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Pricing & Inventory', {
            'fields': (
                ('price', 'compare_price', 'cost_price'),
                ('barcode',),
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders')
            )
        }),
        ('Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
                'condition'
            )
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('Physical Properties', {
            'fields': ('weight', 'dimensions_length', 'dimensions_width', 'dimensions_height'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        })
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('slug', 'created_date', 'modified_date')
        return ('created_date', 'modified_date')

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('product_name',)}


class ReviewRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'subject', 'rating', 'status', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'rating', 'created_at')
    search_fields = ('subject', 'review', 'user__email', 'product__product_name')
    readonly_fields = ('user', 'product', 'subject', 'review', 'rating', 'ip', 'created_at', 'updated_at')
    ordering = ('-created_at',)


class ProductGalleryAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'alt_text', 'image_type', 'order', 'is_active')
    list_editable = ('alt_text', 'image_type', 'order', 'is_active')
    list_filter = ('image_type', 'is_active')
    search_fields = ('product__product_name', 'alt_text')


class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('name', 'slug')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('slug',)
        return ()

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('name',)}


class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'value', 'group', 'order')
    list_editable = ('value', 'group', 'order')
    list_filter = ('group',)
    search_fields = ('product__product_name', 'name', 'value')


class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'sku', 'price', 'compare_price', 'stock', 'is_active')
    list_editable = ('price', 'compare_price', 'stock', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('sku', 'product__product_name')
    readonly_fields = ('sku',)


class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('slug',)
        return ()

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('name',)}


class ProductTagRelationAdmin(admin.ModelAdmin):
    list_display = ('product', 'tag')
    list_filter = ('tag',)
    search_fields = ('product__product_name', 'tag__name')


class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_helpful')
    list_filter = ('is_helpful',)


# Register Admin Classes
admin.site.register(Product, ProductAdmin)
admin.site.register(ComputerProduct, ComputerProductAdmin)
admin.site.register(SoftwareProduct, SoftwareProductAdmin)
admin.site.register(PeripheralProduct, PeripheralProductAdmin)
admin.site.register(ReviewRating, ReviewRatingAdmin)
admin.site.register(ProductGallery, ProductGalleryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(ProductSpecification, ProductSpecificationAdmin)
admin.site.register(ProductVariant, ProductVariantAdmin)
admin.site.register(ProductTag, ProductTagAdmin)
admin.site.register(ProductTagRelation, ProductTagRelationAdmin)
admin.site.register(ReviewHelpful, ReviewHelpfulAdmin)

@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ('slide_number', 'title_main', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    ordering = ('slide_number',)

# Customize admin site
admin.site.site_header = "LiG Store Administration"
admin.site.site_title = "LiG Store Admin"
admin.site.index_title = "Welcome to LiG Store Administration"
