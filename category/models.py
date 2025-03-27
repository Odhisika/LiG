
# Create your models here.
from django.db import models
from django.urls import reverse

# Create your models here.

class Category(models.Model):
    category_name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/categories', blank=True)

    class Meta:
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def get_url(self):
            return reverse('products_by_category', args=[self.slug])

    def __str__(self):
        return self.category_name

class ComputerTypes(models.Model):
    computer_type = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    cat_image = models.ImageField(upload_to='photos/computer_types', blank=True)

    class Meta:
        verbose_name = 'computer type'
        verbose_name_plural = 'computer types'

    def get_url(self):
            return reverse('products_by_computer_type', args=[self.slug])

    def __str__(self):
        return self.computer_type
    



class ResearchTypes(models.Model):
    research_type = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'research type'
        verbose_name_plural = 'research types'

    def get_url(self):
        return reverse('products_by_research_type', args=[self.slug])

    def __str__(self):
        return self.research_type
