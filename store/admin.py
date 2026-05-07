from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import (
    Product, ComputerProduct, SoftwareProduct, PeripheralProduct,
    NetworkingProduct, UPSProduct, SecurityCameraProduct,
    ReviewRating, ProductGallery, Brand, ProductSpecification,
    ProductVariant, ProductTag, ProductTagRelation, ReviewHelpful,
    HomeBanner
)


# ─────────────────────────────────────────────────────────────────────────────
# INLINE CLASSES
# ─────────────────────────────────────────────────────────────────────────────

class ProductGalleryInline(admin.TabularInline):
    model = ProductGallery
    extra = 2
    fields = ('image', 'alt_text', 'image_type', 'order', 'is_active')
    verbose_name = "Product Image"
    verbose_name_plural = "📷 Product Gallery Images"


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 3
    fields = ('group', 'name', 'value', 'order')
    verbose_name = "Specification"
    verbose_name_plural = "📋 Technical Specifications (e.g. Processor: Intel i7)"


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'price', 'compare_price', 'stock', 'attributes', 'is_active')
    readonly_fields = ('sku',)
    verbose_name_plural = "🔀 Product Variants"


class ProductTagRelationInline(admin.TabularInline):
    model = ProductTagRelation
    extra = 1
    fields = ('tag',)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED MIXIN for slug/readonly helpers
# ─────────────────────────────────────────────────────────────────────────────

class ProductAdminMixin:
    extra_readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.extra_readonly_fields) + ['created_date', 'modified_date']
        if obj:
            return ('slug', *fields)
        return tuple(fields)

    def get_prepopulated_fields(self, request, obj=None):
        if obj:
            return {}
        return {'slug': ('product_name',)}

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }


# ─────────────────────────────────────────────────────────────────────────────
# 💻 COMPUTER PRODUCT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ComputerProduct)
class ComputerProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    extra_readonly_fields = ('storefront_destination',)
    list_display = (
        'product_name', 'get_computer_type', 'condition', 'brand',
        'processor_model', 'ram_size', 'storage_capacity', 'price', 'stock', 'is_available'
    )
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ('computer_type', 'condition', 'brand', 'processor_brand', 'is_available', 'is_featured')
    search_fields = ('product_name', 'slug', 'model_number', 'processor_model')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    def get_computer_type(self, obj):
        return obj.computer_type if obj.computer_type else '—'
    get_computer_type.short_description = 'Type'

    def storefront_destination(self, obj):
        if not obj or not obj.computer_type:
            return 'Select the computer type and condition, then save to confirm the exact storefront path.'

        slug = obj.computer_type.slug
        parent_slug = obj.computer_type.parent.slug if obj.computer_type.parent else None
        is_new = obj.condition == 'new' or slug in {'fresh-laptop', 'fresh-desktop'}
        is_used = obj.condition == 'slightly_used' or slug in {'slightly-used-laptop', 'slightly-used-desktop'}

        if slug in {'all-in-one', 'all-in-one-desktop'}:
            return 'Hardware → Computers → All-in-One'

        if slug == 'laptop' or parent_slug == 'laptop':
            if is_new:
                return 'Hardware → Computers → Laptops → Fresh in Box'
            if is_used:
                return 'Hardware → Computers → Laptops → Slightly Used'
            return 'Hardware → Computers → Laptops'

        if slug == 'desktop' or parent_slug == 'desktop':
            if is_new:
                return 'Hardware → Computers → Desktops → Fresh in Box'
            if is_used:
                return 'Hardware → Computers → Desktops → Slightly Used'
            return 'Hardware → Computers → Desktops'

        return 'Hardware → Computers → All Computers'
    storefront_destination.short_description = 'Storefront Destination'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'brand':
            kwargs['queryset'] = Brand.objects.filter(for_computers=True, is_active=True)
        if db_field.name == 'category':
            from category.models import Category
            kwargs['queryset'] = Category.objects.filter(slug='computers')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    fieldsets = (
        ('📝 Basic Information', {
            'fields': (
                ('product_name', 'slug'),
                ('category', 'brand', 'model_number'),
                'short_description',
            ),
            'description': mark_safe(
                'ℹ️ <b>Category</b>: Select the general category (e.g. "Computers"). '
                '<b>Computer Type</b> below determines which sub-page this product appears on '
                '(e.g. Laptops, Desktops, All-in-One, Slightly Used Laptops).'
            )
        }),
        ('🖥️ Computer Classification — REQUIRED FOR CORRECT PAGE ROUTING', {
            'fields': (('computer_type', 'condition'), 'storefront_destination'),
            'description': mark_safe(
                '⚠️ <b>IMPORTANT</b>: Select the Computer Type to determine which page this product appears on.<br>'
                '→ <b>Laptop</b> types appear on the All Computers and Laptops pages.<br>'
                '→ <b>Desktop</b> types appear on the All Computers and Desktops pages.<br>'
                '→ <b>Fresh / Slightly Used</b> sub-types appear on their matching condition pages.<br>'
                '→ <b>All-in-One Desktop</b> appears on the All-in-One page.'
            )
        }),
        ('📄 Description', {
            'fields': ('description',)
        }),
        ('⚙️ Processor', {
            'fields': (
                ('processor_brand', 'processor_model'),
                ('processor_generation', 'processor_cores', 'processor_speed'),
            ),
            'description': 'e.g. Intel, Core i7-1165G7, 11th Gen, 4 cores, 2.8GHz'
        }),
        ('💾 Memory & Storage', {
            'fields': (
                ('ram_size', 'ram_type'),
                ('ram_expandable', 'max_ram'),
                ('storage_capacity', 'storage_type'),
                ('additional_storage_slots',),
            ),
            'description': 'RAM in GB (e.g. 16). Storage in GB (e.g. 512 for 512GB SSD).'
        }),
        ('🎮 Graphics (GPU)', {
            'fields': (('gpu_brand', 'gpu_model', 'gpu_memory'),),
            'description': 'e.g. NVIDIA, RTX 3050, 4GB. Leave blank for integrated graphics.',
            'classes': ('collapse',)
        }),
        ('🖥️ Display', {
            'fields': (
                ('screen_size', 'screen_type'),
                ('screen_resolution', 'refresh_rate'),
                ('touchscreen',),
            ),
            'description': 'Screen size in inches. Resolution e.g. 1920x1080 (FHD).',
            'classes': ('collapse',)
        }),
        ('🔌 Connectivity & Features', {
            'fields': (
                ('operating_system', 'wifi_standard'),
                ('bluetooth_version', 'webcam'),
                ('fingerprint_reader', 'backlit_keyboard'),
                ('battery_life', 'color'),
            ),
            'classes': ('collapse',)
        }),
        ('🛡️ Warranty', {
            'fields': (('warranty_period',),),
            'classes': ('collapse',)
        }),
        ('💰 Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('cost_price', 'barcode'),
            ),
            'description': mark_safe(
                '<b>Price</b>: Selling price. '
                '<b>Compare Price</b>: Original/strikethrough price for discount display. '
                '<b>Cost Price</b>: Your internal cost (not shown to customers).'
            )
        }),
        ('📦 Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders'),
            ),
            'description': 'Set stock level. A low-stock alert fires when stock drops to the threshold.'
        }),
        ('🚦 Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
            )
        }),
        ('🔍 SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('📐 Physical Properties', {
            'fields': (
                ('weight', 'dimensions_length'),
                ('dimensions_width', 'dimensions_height'),
            ),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': (('created_date', 'modified_date'),),
            'classes': ('collapse',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 💾 SOFTWARE PRODUCT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SoftwareProduct)
class SoftwareProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    extra_readonly_fields = ('storefront_destination',)
    list_display = (
        'product_name', 'software_category', 'license_type',
        'version', 'platforms', 'price', 'stock', 'is_available'
    )
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ('software_category', 'license_type', 'condition', 'is_available', 'is_featured')
    search_fields = ('product_name', 'slug', 'developer', 'publisher')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductTagRelationInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            from category.models import Category
            kwargs['queryset'] = Category.objects.filter(slug='software')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def storefront_destination(self, obj):
        if not obj or not obj.software_category:
            return 'Select the software type, then save to confirm the exact storefront path.'

        slug = obj.software_category.slug
        destinations = {
            'operating-system': 'Software → Operating Systems',
            'office-suite': 'Software → Applications → Office Suite',
            'design-creative': 'Software → Applications → Design & Creative',
            'accounting-finance': 'Software → Applications → Accounting & Finance',
            'video-editing': 'Software → Applications → Video Editing',
            'point-of-sale-pos': 'Software → Applications → Point of Sale',
            'antivirus-security': 'Software → Security & Utilities → Antivirus & Security',
            'remote-desktop-vpn': 'Software → Security & Utilities → Remote Desktop & VPN',
            'backup-recovery': 'Software → Security & Utilities → Backup & Recovery',
            'network-management': 'Software → Security & Utilities → Network Management',
            'development-tools': 'Software → Development → Development Tools',
            'database-software': 'Software → Development → Database Software',
        }
        return destinations.get(slug, f'Software → {obj.software_category.software_type}')
    storefront_destination.short_description = 'Storefront Destination'

    fieldsets = (
        ('📝 Basic Information', {
            'fields': (
                ('product_name', 'slug'),
                ('category', 'condition'),
                'short_description',
            ),
            'description': mark_safe('ℹ️ <b>Category</b>: Select the general "Software" category.')
        }),
        ('💾 Software Classification — REQUIRED FOR CORRECT PAGE ROUTING', {
            'fields': (('software_category',), 'storefront_destination'),
            'description': mark_safe(
                '⚠️ <b>IMPORTANT</b>: Select the <b>Software Type</b> to route this product '
                'to the correct software sub-page.<br>'
                '→ <b>Office Suite / Design / Accounting / Video / POS</b> appear under <b>Software → Applications</b>.<br>'
                '→ <b>Antivirus / VPN / Backup / Network Management</b> appear under <b>Software → Security &amp; Utilities</b>.<br>'
                '→ <b>Development Tools / Database Software</b> appear under <b>Software → Development</b>.<br>'
                'If the type does not exist yet, go to <b>Catalogue → Software Types</b> first.'
            )
        }),
        ('📄 Description', {
            'fields': ('description',)
        }),
        ('🔧 Software Details', {
            'fields': (
                ('version', 'license_type'),
                ('platforms', 'max_devices'),
                ('subscription_duration',),
                ('developer', 'publisher'),
            ),
            'description': mark_safe(
                '<b>Platforms</b>: Comma-separated, e.g. windows,macos,linux<br>'
                '<b>Max Devices</b>: How many devices one license covers.<br>'
                '<b>Subscription Duration</b>: In months (12 = yearly).'
            )
        }),
        ('🔑 Digital Delivery', {
            'fields': (
                'download_link',
                ('license_key', 'installation_guide'),
            ),
            'description': 'Provide the download link or license key the customer gets after purchase.',
            'classes': ('collapse',)
        }),
        ('📋 System Requirements', {
            'fields': ('system_requirements',),
            'classes': ('collapse',)
        }),
        ('💰 Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('cost_price', 'barcode'),
            ),
        }),
        ('📦 Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders'),
            ),
        }),
        ('🚦 Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
            )
        }),
        ('🔍 SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': (('created_date', 'modified_date'),),
            'classes': ('collapse',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🔌 PERIPHERAL PRODUCT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(PeripheralProduct)
class PeripheralProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    extra_readonly_fields = ('storefront_destination',)
    list_display = (
        'product_name', 'brand', 'connectivity', 'condition',
        'price', 'stock', 'is_available'
    )
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ('brand', 'connectivity', 'condition', 'is_available', 'is_featured')
    search_fields = ('product_name', 'slug', 'model_number', 'description')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'brand':
            kwargs['queryset'] = Brand.objects.filter(for_peripherals=True, is_active=True)
        if db_field.name == 'category':
            from category.models import Category
            kwargs['queryset'] = Category.objects.filter(slug='peripherals')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def storefront_destination(self, obj):
        return 'Hardware → Accessories'
    storefront_destination.short_description = 'Storefront Destination'

    fieldsets = (
        ('📝 Basic Information', {
            'fields': (
                ('product_name', 'slug'),
                ('category', 'brand', 'model_number'),
                'short_description',
                'storefront_destination',
            ),
            'description': (
                'ℹ️ Peripherals include Mice, Keyboards, Monitors, Headsets, Webcams, '
                'External Drives, Docking Stations, and any PC accessory. '
                'These products appear on the Accessories page.'
            )
        }),
        ('📄 Description', {
            'fields': ('description',)
        }),
        ('🔌 Connectivity & Compatibility', {
            'fields': (('connectivity', 'compatibility'),),
            'description': mark_safe(
                '<b>Connectivity</b>: How it connects (USB, Bluetooth, etc.).<br>'
                '<b>Compatibility</b>: e.g. "Windows 10/11, macOS 12+, Linux".'
            )
        }),
        ('🎨 Physical Details', {
            'fields': (('color', 'material'),),
            'classes': ('collapse',)
        }),
        ('🔋 Power / Battery', {
            'fields': (
                ('battery_required', 'battery_type'),
                ('battery_life', 'power_consumption'),
            ),
            'classes': ('collapse',)
        }),
        ('🛡️ Warranty', {
            'fields': (('warranty_period', 'warranty_type'),),
            'classes': ('collapse',)
        }),
        ('🚦 Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
                'condition',
            )
        }),
        ('💰 Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('cost_price', 'barcode'),
            ),
        }),
        ('📦 Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders'),
            ),
        }),
        ('🔍 SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('📐 Physical Properties', {
            'fields': (
                ('weight', 'dimensions_length'),
                ('dimensions_width', 'dimensions_height'),
            ),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': (('created_date', 'modified_date'),),
            'classes': ('collapse',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 NETWORKING PRODUCT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(NetworkingProduct)
class NetworkingProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    extra_readonly_fields = ('storefront_destination',)
    list_display = (
        'product_name', 'device_type', 'brand', 'max_speed',
        'poe_support', 'wifi_standard', 'price', 'stock', 'is_available'
    )
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ('device_type', 'brand', 'poe_support', 'managed', 'wifi_standard', 'is_available', 'is_featured')
    search_fields = ('product_name', 'slug', 'description', 'model_number')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'brand':
            kwargs['queryset'] = Brand.objects.filter(for_networking=True, is_active=True)
        if db_field.name == 'category':
            from category.models import Category
            kwargs['queryset'] = Category.objects.filter(slug='networking')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def storefront_destination(self, obj):
        if not obj:
            return 'Select the device type, then save to confirm the exact storefront path.'

        destinations = {
            'switch_unmanaged': 'Hardware → Networking → Switches',
            'switch_managed': 'Hardware → Networking → Switches',
            'switch_poe': 'Hardware → Networking → Switches',
            'router': 'Hardware → Networking → Routers & Modems',
            'modem': 'Hardware → Networking → Routers & Modems',
            'modem_router': 'Hardware → Networking → Routers & Modems',
            'access_point': 'Hardware → Networking → Access Points',
        }
        return destinations.get(obj.device_type, 'Hardware → Networking')
    storefront_destination.short_description = 'Storefront Destination'

    fieldsets = (
        ('📝 Basic Information', {
            'fields': (
                ('product_name', 'slug'),
                ('category', 'brand', 'model_number'),
                'short_description',
            ),
            'description': 'ℹ️ Networking products include Switches, Routers, Modems, and Access Points.'
        }),
        ('🌐 Device Classification — REQUIRED', {
            'fields': (('device_type', 'condition'), 'storefront_destination'),
            'description': mark_safe(
                '⚠️ <b>IMPORTANT</b>: Select the correct device type.<br>'
                '→ <b>Switches</b> (managed/unmanaged/PoE) appear on the Switches page.<br>'
                '→ <b>Routers / Modems</b> appear on the Routers &amp; Modems page.<br>'
                '→ <b>Access Points</b> appear on the Access Points page.'
            )
        }),
        ('📄 Description', {
            'fields': ('description',)
        }),
        ('🔌 Ports & Connectivity', {
            'fields': (
                ('total_ports', 'uplink_ports'),
                ('poe_support', 'poe_budget_watts'),
                ('wan_ports', 'dsl_type'),
            ),
            'description': mark_safe(
                '<b>Total Ports</b>: All ports including uplinks (e.g. 24).<br>'
                '<b>PoE Budget</b>: Total watts available for PoE devices (e.g. 370W).<br>'
                '<b>DSL Type</b>: Only for modems — e.g. ADSL2+, VDSL2, Fibre.'
            )
        }),
        ('⚡ Speed & Wi-Fi', {
            'fields': (
                ('max_speed', 'switching_capacity'),
                ('wifi_standard', 'wifi_speed'),
                'dual_band',
            ),
            'description': mark_safe(
                '<b>Max Speed</b>: e.g. 1 Gbps, 10 Gbps.<br>'
                '<b>Switching Capacity</b>: e.g. 48 Gbps (for switches).<br>'
                '<b>Wi-Fi Speed</b>: e.g. AX3000, AC1200. Leave blank for wired-only.'
            )
        }),
        ('⚙️ Management Features', {
            'fields': (('managed', 'vlan_support', 'rack_mountable'),),
            'classes': ('collapse',)
        }),
        ('🛡️ Warranty', {
            'fields': (('warranty_period',),),
            'classes': ('collapse',)
        }),
        ('🚦 Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
            )
        }),
        ('💰 Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('cost_price', 'barcode'),
            ),
        }),
        ('📦 Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders'),
            ),
        }),
        ('🔍 SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('📐 Physical Properties', {
            'fields': (
                ('weight', 'dimensions_length'),
                ('dimensions_width', 'dimensions_height'),
            ),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': (('created_date', 'modified_date'),),
            'classes': ('collapse',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🔋 UPS PRODUCT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UPSProduct)
class UPSProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    extra_readonly_fields = ('storefront_destination',)
    list_display = (
        'product_name', 'brand', 'capacity_va', 'capacity_watts',
        'ups_type', 'form_factor', 'price', 'stock', 'is_available'
    )
    list_editable = ('price', 'stock', 'is_available')
    list_filter = ('ups_type', 'form_factor', 'output_type', 'brand', 'avr', 'lcd_display', 'is_available', 'is_featured')
    search_fields = ('product_name', 'slug', 'description', 'model_number')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'brand':
            kwargs['queryset'] = Brand.objects.filter(for_ups=True, is_active=True)
        if db_field.name == 'category':
            from category.models import Category
            kwargs['queryset'] = Category.objects.filter(slug='ups')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        from category.models import Category
        ups_cat = Category.objects.filter(slug='ups').first()
        if ups_cat:
            initial['category'] = ups_cat.id
        return initial

    def storefront_destination(self, obj):
        return 'Hardware → UPS'
    storefront_destination.short_description = 'Storefront Destination'

    fieldsets = (
        ('📝 Basic Information', {
            'fields': (
                ('product_name', 'slug'),
                ('category', 'brand', 'model_number'),
                'short_description',
                'storefront_destination',
            ),
            'description': mark_safe('ℹ️ UPS products: Standby, Line Interactive, and Online Double Conversion units.<br>'
                                     '⚠️ <b>Note:</b> If you add a new Brand, ensure you tick the <b>"For UPS"</b> checkbox in the brand settings, otherwise it will not appear here.')
        }),
        ('📄 Description', {
            'fields': ('description',)
        }),
        ('⚡ Power Ratings — REQUIRED', {
            'fields': (
                ('capacity_va', 'capacity_watts'),
            ),
            'description': mark_safe(
                '⚠️ <b>IMPORTANT</b>: Enter the VA and Watt ratings.<br>'
                '→ <b>VA</b>: Apparent power (e.g. 1500).<br>'
                '→ <b>Watts</b>: Real power output (e.g. 900). Leave blank if unknown.'
            )
        }),
        ('🔋 UPS Classification', {
            'fields': (
                ('ups_type', 'output_type'),
                ('form_factor', 'condition'),
            ),
            'description': mark_safe(
                '<b>Standby</b>: Basic protection for home/office PCs.<br>'
                '<b>Line Interactive</b>: AVR + battery backup, most popular for SMBs.<br>'
                '<b>Online Double Conversion</b>: Continuous power conditioning for servers.'
            )
        }),
        ('🔌 Battery', {
            'fields': (
                ('battery_type', 'number_of_batteries'),
                'replaceable_battery',
                ('runtime_half_load', 'runtime_full_load'),
            ),
            'description': 'Battery type (e.g. Sealed Lead Acid). Runtime in minutes at 50% and 100% load.'
        }),
        ('🔌 Outlets & Connectivity', {
            'fields': (
                ('num_outlets', 'num_battery_backup_outlets', 'num_surge_only_outlets'),
                ('usb_port', 'network_manageable'),
            ),
            'description': mark_safe(
                '<b>Total Outlets</b>: All output sockets.<br>'
                '<b>Battery Backup Outlets</b>: Sockets with UPS protection.<br>'
                '<b>Surge Only</b>: Sockets with surge protection but no battery backup.'
            )
        }),
        ('🛡️ Protection Features', {
            'fields': (
                ('surge_protection_joules', 'avr'),
                ('lcd_display', 'audible_alarm'),
            ),
            'classes': ('collapse',)
        }),
        ('🛡️ Warranty', {
            'fields': (('warranty_period',),),
            'classes': ('collapse',)
        }),
        ('🚦 Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
            )
        }),
        ('💰 Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('cost_price', 'barcode'),
            ),
        }),
        ('📦 Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders'),
            ),
        }),
        ('🔍 SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('📐 Physical Properties', {
            'fields': (
                ('weight', 'dimensions_length'),
                ('dimensions_width', 'dimensions_height'),
            ),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': (('created_date', 'modified_date'),),
            'classes': ('collapse',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 📷 SECURITY CAMERA / CCTV ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(SecurityCameraProduct)
class SecurityCameraProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    extra_readonly_fields = ('storefront_destination',)
    list_display = (
        'product_name', 'camera_type', 'brand', 'resolution',
        'night_vision', 'weatherproof', 'price', 'stock', 'is_available'
    )
    list_editable = ('price', 'stock', 'is_available')
    list_filter = (
        'camera_type', 'brand', 'resolution', 'night_vision',
        'weatherproof', 'motion_detection', 'ai_detection', 'is_available'
    )
    search_fields = ('product_name', 'slug', 'description', 'model_number')
    ordering = ('-created_date',)
    readonly_fields = ('created_date', 'modified_date')
    inlines = [ProductGalleryInline, ProductSpecificationInline, ProductTagRelationInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'brand':
            kwargs['queryset'] = Brand.objects.filter(for_security=True, is_active=True)
        if db_field.name == 'category':
            from category.models import Category
            kwargs['queryset'] = Category.objects.filter(slug='security-cctv')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def storefront_destination(self, obj):
        if not obj:
            return 'Select the camera type, then save to confirm the exact storefront path.'

        if obj.camera_type == 'cctv_kit':
            return 'Hardware → Security Cameras → CCTV Kits'
        if obj.camera_type in {'nvr', 'dvr'}:
            return 'Hardware → Security Cameras → NVR / DVR'
        return 'Hardware → Security Cameras → IP Cameras'
    storefront_destination.short_description = 'Storefront Destination'

    fieldsets = (
        ('📝 Basic Information', {
            'fields': (
                ('product_name', 'slug'),
                ('category', 'brand', 'model_number'),
                'short_description',
            ),
            'description': (
                'ℹ️ Security products: IP Cameras, Dome/Bullet Cameras, PTZ, NVRs, DVRs, Complete CCTV Kits.'
            )
        }),
        ('📷 Camera Classification — REQUIRED', {
            'fields': (('camera_type', 'resolution', 'condition'), 'storefront_destination'),
            'description': mark_safe(
                '⚠️ <b>IMPORTANT</b>: Select the camera type to route to the correct CCTV section.<br>'
                '→ <b>IP / PTZ / Dome / Bullet / Fisheye / Doorbell Cameras</b> → IP Cameras page.<br>'
                '→ <b>Complete CCTV Kits</b> → CCTV Kits page.<br>'
                '→ <b>NVR / DVR</b> → NVR / DVR page.'
            )
        }),
        ('📄 Description', {
            'fields': ('description',)
        }),
        ('👁️ Vision', {
            'fields': (
                ('night_vision', 'night_vision_range'),
                'wide_angle',
            ),
            'description': 'Night vision range in metres. Wide angle in degrees e.g. 120°.'
        }),
        ('🔌 Connectivity & Power', {
            'fields': (('connectivity', 'poe_powered'),),
            'description': 'Connectivity: e.g. "Wired PoE", "Wi-Fi 2.4/5GHz", "4G LTE".'
        }),
        ('💾 Storage', {
            'fields': (('storage_type', 'max_sd_card_gb'),),
            'classes': ('collapse',)
        }),
        ('📦 Kit Details (NVR/DVR/Complete Kits Only)', {
            'fields': (
                ('number_of_cameras', 'channels'),
                ('hdd_included_tb',),
            ),
            'classes': ('collapse',),
            'description': 'Only fill for kits, NVRs, or DVRs that come with cameras or HDDs.'
        }),
        ('🤖 Smart Features', {
            'fields': (
                ('motion_detection', 'two_way_audio'),
                'ai_detection',
                ('weatherproof', 'weatherproof_rating'),
            ),
            'description': 'Weatherproof rating: e.g. IP66, IP67, IK10.'
        }),
        ('🛡️ Warranty', {
            'fields': (('warranty_period',),),
            'classes': ('collapse',)
        }),
        ('🚦 Product Status', {
            'fields': (
                ('is_available', 'is_featured'),
                ('requires_shipping', 'is_digital'),
            )
        }),
        ('💰 Pricing', {
            'fields': (
                ('price', 'compare_price'),
                ('cost_price', 'barcode'),
            ),
        }),
        ('📦 Inventory', {
            'fields': (
                ('stock', 'low_stock_threshold'),
                ('track_inventory', 'allow_backorders'),
            ),
            'description': 'Second inventory section.'
        }),
        ('🔍 SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'tags'),
            'classes': ('collapse',)
        }),
        ('📐 Physical Properties', {
            'fields': (
                ('weight', 'dimensions_length'),
                ('dimensions_width', 'dimensions_height'),
            ),
            'classes': ('collapse',)
        }),
        ('🕒 Timestamps', {
            'fields': (('created_date', 'modified_date'),),
            'classes': ('collapse',)
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# CATALOGUE & UTILITY ADMINS
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'for_computers', 'for_networking', 'for_ups', 'for_security', 'for_peripherals', 'for_software', 'website')
    list_editable = ('is_active', 'for_computers', 'for_networking', 'for_ups', 'for_security', 'for_peripherals', 'for_software')
    list_filter = ('is_active', 'for_computers', 'for_networking', 'for_ups', 'for_security', 'for_peripherals', 'for_software')
    search_fields = ('name', 'slug')

    fieldsets = (
        ('Brand Details', {
            'fields': ('name', 'slug', 'logo', 'description', 'website', 'is_active')
        }),
        ('Product Groups — Tick all that apply', {
            'fields': ('for_computers', 'for_networking', 'for_ups', 'for_security', 'for_peripherals', 'for_software'),
            'description': mark_safe(
                '⚠️ Tick the sections this brand belongs to. '
                'The brand will only appear in the brand dropdown for the ticked product types.'
            )
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        return ('slug',) if obj else ()

    def get_prepopulated_fields(self, request, obj=None):
        return {} if obj else {'slug': ('name',)}


@admin.register(ReviewRating)
class ReviewRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'subject', 'rating', 'status', 'created_at')
    list_editable = ('status',)
    list_filter = ('status', 'rating', 'created_at')
    search_fields = ('subject', 'review', 'user__email', 'product__product_name')
    readonly_fields = ('user', 'product', 'subject', 'review', 'rating', 'ip', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(ProductGallery)
class ProductGalleryAdmin(admin.ModelAdmin):
    list_display = ('product', 'image', 'alt_text', 'image_type', 'order', 'is_active')
    list_editable = ('alt_text', 'image_type', 'order', 'is_active')
    list_filter = ('image_type', 'is_active')
    search_fields = ('product__product_name', 'alt_text')


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    list_display = ('product', 'group', 'name', 'value', 'order')
    list_editable = ('value', 'group', 'order')
    list_filter = ('group',)
    search_fields = ('product__product_name', 'name', 'value')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'sku', 'price', 'compare_price', 'stock', 'is_active')
    list_editable = ('price', 'compare_price', 'stock', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('sku', 'product__product_name')
    readonly_fields = ('sku',)


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')

    def get_readonly_fields(self, request, obj=None):
        return ('slug',) if obj else ()

    def get_prepopulated_fields(self, request, obj=None):
        return {} if obj else {'slug': ('name',)}


@admin.register(ProductTagRelation)
class ProductTagRelationAdmin(admin.ModelAdmin):
    list_display = ('product', 'tag')
    list_filter = ('tag',)
    search_fields = ('product__product_name', 'tag__name')


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'is_helpful')
    list_filter = ('is_helpful',)


@admin.register(HomeBanner)
class HomeBannerAdmin(admin.ModelAdmin):
    list_display = ('slide_number', 'title_main', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    ordering = ('slide_number',)


# NOTE: The base Product model is intentionally NOT registered.
# Always use the specific product type admins above.

admin.site.site_header = "LiG Store — Product Management"
admin.site.site_title = "LiG Store Admin"
admin.site.index_title = "Welcome to LiG Store Administration"
