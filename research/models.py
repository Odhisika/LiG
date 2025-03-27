from django.db import models
from django.contrib.auth.models import User
from froala_editor.fields import FroalaField
from category.models import ResearchTypes
from accounts.models import Account
from .helpers import *



class BlogModel(models.Model):
    title = models.CharField(max_length=1000)
    content = FroalaField()
    slug = models.SlugField(max_length=1000, unique=True)
    research_type = models.ForeignKey(
    'category.ResearchTypes', on_delete=models.CASCADE, )
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    upload_to = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.title


    def save(self, *args, **kwargs):
     if not self.slug:
      self.slug = generate_slug(self.title)
     super(BlogModel, self).save(*args, **kwargs)







class ProjectBooking(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    university = models.CharField(max_length=255)
    project_details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.project_details[:30]}"
