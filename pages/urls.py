from django.urls import path
from . import views

urlpatterns = [
    path('about/', views.about, name='about'),
    path('help/', views.help_center, name='help_center'),
    path('help/<slug:slug>/', views.help_article_detail, name='help_article_detail'),
    path('services/web-development/', views.web_development, name='web_development'),
    path('services/mobile-apps/', views.mobile_apps, name='mobile_apps'),
    path('services/cloud-solutions/', views.cloud_solutions, name='cloud_solutions'),
    path('services/it-consulting/', views.it_consulting, name='it_consulting'),
    path('services/digital-strategy/', views.digital_strategy, name='digital_strategy'),
    path('<str:page_type>/', views.policy_page, name='policy_page'),
]
