
from django.contrib import admin
from .models import Category, ComputerTypes, ResearchTypes

# Register your models here.

class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('category_name', 'slug')

class ComputerTypesAdmin(admin.ModelAdmin):   
    prepopulated_fields = {'slug': ('computer_type',)}
    list_display = ('computer_type', 'slug')


class ResearchTypesAdmin(admin.ModelAdmin):   
    prepopulated_fields = {'slug': ('research_type',)}
    list_display = ('research_type', 'slug')

admin.site.register(Category, CategoryAdmin)
admin.site.register(ComputerTypes, ComputerTypesAdmin)
admin.site.register(ResearchTypes, ResearchTypesAdmin)