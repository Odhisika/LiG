from django.db import models
from django.urls import reverse
from django.db.models import Avg, Count
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from category.models import Category, ComputerTypes
from accounts.models import Account


# Base Product Model
class Product(models.Model):
    # Basic Information
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(max_length=1000, blank=True)  
    short_description = models.CharField(max_length=255, blank=True)  
    
    # Pricing and Inventory
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, 
                                       help_text="Original price for discount display")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                   help_text="Internal cost for profit calculations")
    
    # Inventory Management
    sku = models.CharField(max_length=50, unique=True, help_text="Stock Keeping Unit", default='temp-sku')
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    stock = models.IntegerField(validators=[MinValueValidator(0)])
    low_stock_threshold = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    track_inventory = models.BooleanField(default=True)
    allow_backorders = models.BooleanField(default=False)
    
    # Product Status
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    requires_shipping = models.BooleanField(default=True)
    is_digital = models.BooleanField(default=False)
    
    # SEO and Marketing
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Organization
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Physical Properties
    weight = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True, 
                                help_text="Weight in kg")
    dimensions_length = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, 
                                          help_text="Length in cm")
    dimensions_width = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True,
                                         help_text="Width in cm") 
    dimensions_height = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True,
                                          help_text="Height in cm")
    
    # Images
    images = models.ImageField(upload_to='photos/products', blank=True, null=True)

    
    # Timestamps
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_date']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['is_available', 'stock']),
            models.Index(fields=['category', 'is_available']),
        ]

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock > 0 or self.allow_backorders

    def is_low_stock(self):
        return self.track_inventory and self.stock <= self.low_stock_threshold

    def get_discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0
    
    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

    def is_in_stock(self):
        if not self.track_inventory:
            return True
        return self.stock > 0 or self.allow_backorders

    def is_low_stock(self):
        return self.track_inventory and self.stock <= self.low_stock_threshold

    def get_discount_percentage(self):
        if self.compare_price and self.compare_price > self.price:
            return round(((self.compare_price - self.price) / self.compare_price) * 100)
        return 0

    def average_review(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Avg('rating'))
        return round(float(reviews['average']), 1) if reviews['average'] else 0

    def count_review(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(count=Count('id'))
        return int(reviews['count']) if reviews['count'] else 0

    # ADD THIS METHOD
    @property
    def primary_image_url(self):
        """Return the primary image URL for the product"""
        # First, check if the main images field has an image
        if self.images:
            return self.images.url
        
        # Then check gallery images
        first_gallery = self.gallery_images.filter(is_active=True).first()
        if first_gallery:
            return first_gallery.image.url
        
        # Return a default image path (make sure this file exists in your static files)
        return '/static/images/default-product.jpg'  # or use a placeholder service

    # Alternative method name for compatibility
    def get_primary_image_url(self):
        return self.primary_image_url

    def average_review(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Avg('rating'))
        return round(float(reviews['average']), 1) if reviews['average'] else 0

    def count_review(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(count=Count('id'))
        return int(reviews['count']) if reviews['count'] else 0


# Brand Model (normalized)
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='photos/brands', blank=True, null=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


# Specifications Model (flexible key-value pairs)
class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100)  # e.g., "Processor", "RAM", "Screen Size"
    value = models.CharField(max_length=200)  # e.g., "Intel i7", "16GB", "15.6 inches"
    group = models.CharField(max_length=50, blank=True)  # e.g., "Performance", "Display", "Connectivity"
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['group', 'order', 'name']
        unique_together = ['product', 'name']
    
    def __str__(self):
        return f"{self.product.product_name} - {self.name}: {self.value}"


# Model for Computers (Laptops, Desktops, etc.)
class ComputerProduct(Product):
    PROCESSOR_BRANDS = [
        ('intel', 'Intel'),
        ('amd', 'AMD'),
        ('apple', 'Apple Silicon'),
        ('other', 'Other'),
    ]
    
    STORAGE_TYPES = [
        ('hdd', 'HDD'),
        ('ssd', 'SSD'),
        ('hybrid', 'Hybrid'),
        ('emmc', 'eMMC'),
    ]
    
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model_number = models.CharField(max_length=100, blank=True)
    
    # Processor
    processor_brand = models.CharField(max_length=20, choices=PROCESSOR_BRANDS, blank=True)
    processor_model = models.CharField(max_length=100, blank=True)
    processor_generation = models.CharField(max_length=50, blank=True)
    processor_cores = models.PositiveIntegerField(blank=True, null=True)
    processor_speed = models.CharField(max_length=50, blank=True)  # e.g., "2.4GHz"
    
    # Memory and Storage
    ram_size = models.PositiveIntegerField(blank=True, null=True, help_text="RAM in GB")
    ram_type = models.CharField(max_length=20, blank=True)  # DDR4, DDR5, etc.
    ram_expandable = models.BooleanField(default=False)
    max_ram = models.PositiveIntegerField(blank=True, null=True, help_text="Maximum RAM in GB")
    
    storage_capacity = models.PositiveIntegerField(blank=True, null=True, help_text="Storage in GB")
    storage_type = models.CharField(max_length=20, choices=STORAGE_TYPES, blank=True)
    additional_storage_slots = models.PositiveIntegerField(default=0)
    
    # Graphics
    gpu_brand = models.CharField(max_length=50, blank=True)  # NVIDIA, AMD, Intel
    gpu_model = models.CharField(max_length=100, blank=True)
    gpu_memory = models.PositiveIntegerField(blank=True, null=True, help_text="GPU memory in GB")
    
    # Display
    screen_size = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    screen_resolution = models.CharField(max_length=50, blank=True)  # 1920x1080, 4K, etc.
    screen_type = models.CharField(max_length=50, blank=True)  # LCD, OLED, etc.
    refresh_rate = models.PositiveIntegerField(blank=True, null=True, help_text="Hz")
    touchscreen = models.BooleanField(default=False)
    
    # System
    computer_type = models.ForeignKey(ComputerTypes, on_delete=models.CASCADE, default=1)
    operating_system = models.CharField(max_length=100, blank=True, default='Windows 10')
    
    # Features
    wifi_standard = models.CharField(max_length=20, blank=True)  # Wi-Fi 6, etc.
    bluetooth_version = models.CharField(max_length=10, blank=True)
    webcam = models.BooleanField(default=False)
    fingerprint_reader = models.BooleanField(default=False)
    backlit_keyboard = models.BooleanField(default=False)
    
    # Physical
    battery_life = models.CharField(max_length=50, blank=True)  # "Up to 10 hours"
    color = models.CharField(max_length=50, blank=True)
    
    # Warranty and Support
    warranty_period = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.brand.name} {self.product_name}"


# Model for Software
class SoftwareProduct(Product):
    LICENSE_TYPES = [
        ('one_time', 'One-time Purchase'),
        ('subscription_monthly', 'Monthly Subscription'),
        ('subscription_yearly', 'Yearly Subscription'),
        ('freemium', 'Freemium'),
        ('open_source', 'Open Source'),
    ]
    
    PLATFORMS = [
        ('windows', 'Windows'),
        ('macos', 'macOS'),
        ('linux', 'Linux'),
        ('web', 'Web Browser'),
        ('mobile', 'Mobile'),
        ('cross_platform', 'Cross Platform'),
    ]
    
    software_type = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    license_type = models.CharField(max_length=30, choices=LICENSE_TYPES)
    platforms = models.CharField(max_length=200, help_text="Comma-separated platform list", default='web')
    system_requirements = models.TextField(blank=True)
    
    # Digital delivery
    download_link = models.URLField(blank=True, null=True)
    license_key = models.CharField(max_length=200, blank=True)
    installation_guide = models.URLField(blank=True, null=True)
    
    # Subscription details
    subscription_duration = models.PositiveIntegerField(blank=True, null=True, 
                                                       help_text="Duration in months")
    max_devices = models.PositiveIntegerField(blank=True, null=True)
    
    # Developer/Publisher
    developer = models.CharField(max_length=100, blank=True)
    publisher = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.software_type} - {self.product_name} ({self.version})"


# Model for Peripherals
class PeripheralProduct(Product):
    CONNECTIVITY_TYPES = [
        ('wired_usb', 'Wired USB'),
        ('wired_usbc', 'Wired USB-C'),
        ('wireless_2.4ghz', 'Wireless 2.4GHz'),
        ('bluetooth', 'Bluetooth'),
        ('wifi', 'Wi-Fi'),
        ('thunderbolt', 'Thunderbolt'),
        ('hdmi', 'HDMI'),
        ('displayport', 'DisplayPort'),
    ]
    
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model_number = models.CharField(max_length=100, blank=True)
    connectivity = models.CharField(max_length=30, choices=CONNECTIVITY_TYPES, blank=True, default='wired_usb')
    compatibility = models.TextField(help_text="Compatible devices/systems")
    
    # Common peripheral specs
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)
    
    # Warranty
    warranty_period = models.CharField(max_length=100, blank=True)
    warranty_type = models.CharField(max_length=100, blank=True)  # Limited, Full, etc.
    
    # Power
    battery_required = models.BooleanField(default=False)
    battery_type = models.CharField(max_length=50, blank=True)
    battery_life = models.CharField(max_length=100, blank=True)
    power_consumption = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"{self.brand.name} {self.product_name}"


# Enhanced Review and Rating System
class ReviewRating(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=1000, blank=True)
    rating = models.IntegerField(choices=RATING_CHOICES, validators=[MinValueValidator(1), MaxValueValidator(5)])
    
    # Helpful votes
    helpful_count = models.PositiveIntegerField(default=0)
    
    # Verification
    verified_purchase = models.BooleanField(default=False)
    
    # Moderation
    status = models.BooleanField(default=True)
    moderated_by = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='moderated_reviews')
    
    # Metadata
    ip = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'user']  # One review per user per product
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.product_name} - {self.rating}/5 by {self.user.username}"


# Review Helpfulness Votes
class ReviewHelpful(models.Model):
    review = models.ForeignKey(ReviewRating, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()  # True for helpful, False for not helpful
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']


# Enhanced Product Gallery
class ProductGallery(models.Model):
    IMAGE_TYPES = [
        ('main', 'Main Product Image'),
        ('gallery', 'Gallery Image'),
        ('thumbnail', 'Thumbnail'),
        ('zoom', 'Zoom Image'),
        ('lifestyle', 'Lifestyle Image'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='store/products', max_length=255)
    alt_text = models.CharField(max_length=255, blank=True)
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='gallery')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"{self.product.product_name} - {self.image_type}"


# Product Variants (for products with multiple options like color, size, etc.)
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=50, unique=True)
    
    # Variant-specific pricing and inventory
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock = models.IntegerField(default=0)
    
    # Variant attributes (stored as JSON or separate model)
    attributes = models.JSONField(default=dict, help_text="e.g., {'color': 'red', 'size': 'large'}")
    
    # Images specific to this variant
    image = models.ImageField(upload_to='store/variants', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        attrs = ', '.join([f"{k}: {v}" for k, v in self.attributes.items()])
        return f"{self.product.product_name} ({attrs})"
    
    def get_price(self):
        return self.price if self.price else self.product.price


# Product Categories Enhancement (if you want to improve your existing Category model)
class ProductTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    slug = models.SlugField(max_length=50, unique=True)
    color = models.CharField(max_length=7, blank=True, help_text="Hex color code")
    
    def __str__(self):
        return self.name


# Many-to-many relationship for tags
class ProductTagRelation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    tag = models.ForeignKey(ProductTag, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['product', 'tag']


# In Product model

@property
def primary_image_url(self):
    if self.images:
        return self.images.url
    first_gallery = self.gallery_images.first()
    if first_gallery:
        return first_gallery.image.url
    return 'https://via.placeholder.com/300x300?text=No+Image'
