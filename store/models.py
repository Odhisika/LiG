from django.db import models
from django.urls import reverse
from django.db.models import Avg, Count
from category.models import Category, ComputerTypes
from accounts.models import Account

# Base Product Model
class Product(models.Model):
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    images = models.ImageField(upload_to='photos/products', blank=True, null=True)
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

    def averageReview(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(average=Avg('rating'))
        return float(reviews['average']) if reviews['average'] else 0

    def countReview(self):
        reviews = ReviewRating.objects.filter(product=self, status=True).aggregate(count=Count('id'))
        return int(reviews['count']) if reviews['count'] else 0


# Model for Computers (Laptops, Desktops, etc.)
class ComputerProduct(Product):
    brand = models.CharField(max_length=100)
    processor = models.CharField(max_length=100)  
    ram = models.CharField(max_length=50)  
    storage = models.CharField(max_length=100)
    computer_type = models.ForeignKey(ComputerTypes, on_delete=models.CASCADE, default=1 )  # Example: Laptop, Desktop, All-in-One  
    gpu = models.CharField(max_length=100, blank=True, null=True)  
    screen_size = models.CharField(max_length=50)  
    operating_system = models.CharField(max_length=100, blank=True, null=True)  # Example: Windows 11, macOS

    def __str__(self):
        return f"{self.brand} {self.product_name}"


# Model for Software
class SoftwareProduct(Product):
    software_type = models.CharField(max_length=100)  # Example: Antivirus, OS, Office Suite
    version = models.CharField(max_length=50)  # Example: Windows 11 Pro, Adobe Photoshop 2023
    license_type = models.CharField(max_length=50, choices=[("One-time", "One-time"), ("Subscription", "Subscription")])
    platform = models.CharField(max_length=100)  # Example: Windows, macOS, Linux
    download_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.software_type} - {self.product_name} ({self.version})"


# Model for Peripherals (Keyboards, Mice, Monitors, etc.)
class PeripheralProduct(Product):
    brand = models.CharField(max_length=100)
    connectivity = models.CharField(max_length=100, blank=True, null=True)  # Example: Wired, Wireless, Bluetooth
    compatibility = models.CharField(max_length=200)  # Example: Windows, macOS, PlayStation, Xbox
    warranty = models.CharField(max_length=100, blank=True, null=True)  # Example: 1 Year, 2 Years

    def __str__(self):
        return f"{self.brand} {self.product_name}"


# Review and Rating System
class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.CharField(max_length=20, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.subject


# Product Gallery
class ProductGallery(models.Model):
    product = models.ForeignKey(Product, default=None, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='store/products', max_length=255)

    def __str__(self):
        return self.product.product_name

    class Meta:
        verbose_name = 'productgallery'
        verbose_name_plural = 'product gallery'
