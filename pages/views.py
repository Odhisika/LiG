from django.shortcuts import render, get_object_or_404
from .models import AboutPage, HelpCategory, HelpArticle, PolicyPage


def about(request):
    try:
        about_page = AboutPage.objects.filter(is_active=True).first()
    except AboutPage.DoesNotExist:
        about_page = None
    return render(request, 'pages/about.html', {'about_page': about_page})


def help_center(request):
    categories = HelpCategory.objects.filter(is_active=True).prefetch_related('articles')
    query = request.GET.get('q', '').strip()
    search_results = None
    if query:
        search_results = HelpArticle.objects.filter(
            is_active=True,
            title__icontains=query
        ).select_related('category')[:20]
    return render(request, 'pages/help_center.html', {
        'categories': categories,
        'query': query,
        'search_results': search_results,
    })


def help_article_detail(request, slug):
    article = get_object_or_404(HelpArticle, slug=slug, is_active=True)
    article.views_count += 1
    article.save(update_fields=['views_count'])
    return render(request, 'pages/help_article_detail.html', {'article': article})


def web_development(request):
    return render(request, 'pages/services/web_development.html')


def mobile_apps(request):
    return render(request, 'pages/services/mobile_apps.html')


def cloud_solutions(request):
    return render(request, 'pages/services/cloud_solutions.html')


def it_consulting(request):
    return render(request, 'pages/services/it_consulting.html')


def digital_strategy(request):
    return render(request, 'pages/services/digital_strategy.html')


def policy_page(request, page_type):
    page = get_object_or_404(PolicyPage, page_type=page_type, is_active=True)
    return render(request, 'pages/policy.html', {'page': page})
