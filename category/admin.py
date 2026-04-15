from django.contrib import admin
from .models import Category, ComputerTypes, ResearchTypes, SoftwareTypes


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('category_name',)}
    list_display = ('category_name', 'slug', 'is_active', 'is_featured', 'sort_order')
    list_editable = ('is_active', 'is_featured', 'sort_order')
    list_filter = ('is_active', 'is_featured')
    search_fields = ('category_name', 'slug')
    ordering = ('sort_order', 'category_name')


@admin.register(ComputerTypes)
class ComputerTypesAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('computer_type',)}
    list_display = ('get_full_name', 'slug', 'parent', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    list_filter = ('parent', 'is_active')
    search_fields = ('computer_type', 'slug')
    ordering = ('parent__sort_order', 'sort_order', 'computer_type')

    def get_full_name(self, obj):
        if obj.parent:
            return f"↳ {obj.computer_type}  (under {obj.parent.computer_type})"
        return obj.computer_type
    get_full_name.short_description = 'Computer Type'

    fieldsets = (
        ('Computer Type Info', {
            'fields': ('computer_type', 'slug', 'description', 'cat_image'),
            'description': (
                'Examples: <b>Laptop</b>, <b>Desktop</b> as top-level types. '
                'Then <b>Fresh Laptop</b> or <b>Slightly Used Laptop</b> as children of <b>Laptop</b>.'
            )
        }),
        ('Hierarchy', {
            'fields': ('parent',),
            'description': (
                'Leave <b>Parent</b> blank for top-level types (e.g. Laptop, Desktop). '
                'For sub-types like "Slightly Used Laptop", set parent to "Laptop".'
            )
        }),
        ('Display Settings', {
            'fields': ('is_active', 'sort_order')
        }),
    )


@admin.register(SoftwareTypes)
class SoftwareTypesAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('software_type',)}
    list_display = ('software_type', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('software_type', 'slug')
    ordering = ('sort_order', 'software_type')

    fieldsets = (
        ('Software Type Info', {
            'fields': ('software_type', 'slug', 'description', 'cat_image'),
            'description': (
                'Create a software category here first, then assign it to a '
                '<b>Software Product</b> during upload. '
                'Examples: Antivirus, Office Suite, Design & Creative, Security Software.'
            )
        }),
        ('Display Settings', {
            'fields': ('is_active', 'sort_order')
        }),
    )


@admin.register(ResearchTypes)
class ResearchTypesAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('research_type',)}
    list_display = ('research_type', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    list_filter = ('is_active',)
    search_fields = ('research_type', 'slug')
    ordering = ('sort_order', 'research_type')