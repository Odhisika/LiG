from django.contrib import admin
from .models import Visitor, PageView, DailyStats


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'ip_address', 'user', 'page_views', 'first_visit', 'last_visit')
    list_filter = ('first_visit',)
    search_fields = ('ip_address', 'session_id', 'user__email')
    readonly_fields = ('session_id', 'first_visit', 'last_visit')
    date_hierarchy = 'first_visit'


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ('visitor', 'path', 'title', 'viewed_at')
    list_filter = ('viewed_at', 'path')
    search_fields = ('path', 'title')
    readonly_fields = ('viewed_at',)
    date_hierarchy = 'viewed_at'


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = ('date', 'unique_visitors', 'page_views', 'total_orders', 'total_revenue')
    list_filter = ('date',)
    readonly_fields = ('date',)
    date_hierarchy = 'date'
