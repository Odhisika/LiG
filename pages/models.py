from django.db import models
from django.utils.text import slugify
from froala_editor.fields import FroalaField


class AboutPage(models.Model):
    title = models.CharField(max_length=200, default='About Us')
    hero_title = models.CharField(max_length=200, default='About LuckyTech Innovation Ground')
    hero_subtitle = models.TextField(default='Empowering businesses through innovative technology solutions.')
    mission = models.TextField(blank=True, default='')
    vision = models.TextField(blank=True, default='')
    values = models.TextField(blank=True, default='')
    story = FroalaField(blank=True, default='')
    team_section_title = models.CharField(max_length=200, default='Our Team')
    team_section_content = FroalaField(blank=True, default='')
    meta_description = models.CharField(max_length=160, default='Learn about LuckyTech Innovation Ground - our mission, vision, and team.')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'About Page'
        verbose_name_plural = 'About Pages'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.pk and AboutPage.objects.exists():
            raise ValueError('Only one About Page instance is allowed.')
        super().save(*args, **kwargs)


class PolicyPage(models.Model):
    PAGE_TYPES = [
        ('privacy', 'Privacy Policy'),
        ('terms', 'Terms of Service'),
        ('cookies', 'Cookie Policy'),
    ]
    page_type = models.CharField(max_length=20, choices=PAGE_TYPES, unique=True)
    title = models.CharField(max_length=200)
    content = FroalaField()
    meta_description = models.CharField(max_length=160, blank=True, default='')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Policy Page'
        verbose_name_plural = 'Policy Pages'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return f'/{self.page_type}/'


class HelpCategory(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon = models.CharField(max_length=50, default='fa-question-circle', help_text='Font Awesome icon class (e.g. fa-shopping-cart)')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Help Category'
        verbose_name_plural = 'Help Categories'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class HelpArticle(models.Model):
    category = models.ForeignKey(HelpCategory, on_delete=models.CASCADE, related_name='articles')
    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, blank=True)
    content = FroalaField()
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    views_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Help Article'
        verbose_name_plural = 'Help Articles'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
