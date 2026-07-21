from django.contrib import admin
from .models import AboutPage, HelpCategory, HelpArticle, PolicyPage


class HelpArticleInline(admin.TabularInline):
    model = HelpArticle
    extra = 0
    fields = ['title', 'slug', 'order', 'is_active']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'updated_at']
    list_filter = ['is_active']
    list_editable = ['is_active']
    fieldsets = (
        ('Hero Section', {
            'fields': ('hero_title', 'hero_subtitle')
        }),
        ('Content', {
            'fields': ('mission', 'vision', 'values', 'story', 'team_section_title', 'team_section_content')
        }),
        ('SEO', {
            'fields': ('meta_description',)
        }),
        ('Settings', {
            'fields': ('title', 'is_active')
        }),
    )


@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'slug', 'order', 'is_active', 'article_count']
    list_filter = ['is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [HelpArticleInline]
    search_fields = ['title']

    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = 'Articles'


@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'order', 'is_active', 'views_count', 'updated_at']
    list_filter = ['category', 'is_active']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ['title', 'content']
    readonly_fields = ['views_count', 'created_at', 'updated_at']
    fieldsets = (
        ('Content', {
            'fields': ('category', 'title', 'slug', 'content')
        }),
        ('Settings', {
            'fields': ('order', 'is_active')
        }),
        ('Statistics', {
            'fields': ('views_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PolicyPage)
class PolicyPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'page_type', 'is_active', 'updated_at']
    list_filter = ['is_active', 'page_type']
    list_editable = ['is_active']
    search_fields = ['title', 'content']
    readonly_fields = ['updated_at']
