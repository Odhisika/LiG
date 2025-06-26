from django.db import models
from django.urls import reverse


class Category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/categories', blank=True)
    
    # New additions
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'
        ordering = ['sort_order', 'category_name']

    def get_url(self):
        return reverse('products_by_category', args=[self.slug])

    def __str__(self):
        return self.category_name


class ComputerTypes(models.Model):
    computer_type = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/computer_types', blank=True)
    
    # New additions
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
   

    class Meta:
        verbose_name = 'computer type'
        verbose_name_plural = 'computer types'
        ordering = ['sort_order', 'computer_type']

    def get_url(self):
        return reverse('products_by_computer_type', args=[self.slug])

    def __str__(self):
        return self.computer_type


class SoftwareTypes(models.Model):
    software_type = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/software_types', blank=True)
    
    # New additions
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    

    class Meta:
        verbose_name = 'Software type'
        verbose_name_plural = 'Software types'
        ordering = ['sort_order', 'software_type']

    def get_url(self):
        return reverse('products_by_software_type', args=[self.slug])

    def __str__(self):
        return self.software_type


class ResearchTypes(models.Model):
    research_type = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    
    # New additions
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'research type'
        verbose_name_plural = 'research types'
        ordering = ['sort_order', 'research_type']

    def get_url(self):
        return reverse('products_by_research_type', args=[self.slug])

    def __str__(self):
        return self.research_type