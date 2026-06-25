"""
URL configuration for LiG project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.sitemaps.views import sitemap
from store.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap
from django.views.generic import TemplateView

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'pages': StaticViewSitemap,
}



urlpatterns = [
    path('securelogin/', admin.site.urls),
    path('dashboard/', include('analytics.urls')),
    path('', views.home, name='home'),
    path('store/', include('store.urls')),
    path("cart/", include("cart.urls")),
    path('payments/', include('payment.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/', include('accounts.urls')),
    path('froala_editor/',include('froala_editor.urls')),
    path('research/', include('research.urls')),   
    path("sitemap.xml", sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')), 
    path("googlec8d038f8f2eae61f.html", TemplateView.as_view(
        template_name="googlec8d038f8f2eae61f.html", content_type="text/html"
    )),
    
    

    # Navigation hardware links
    path('hardware/desktops/', views.desktops, name='desktops'),
    path('hardware/laptops/', views.laptops, name='laptops'),
    path('hardware/computers/', views.computers_all, name='computers_all'),
    path('hardware/all-in-one/', views.all_in_one_computers, name='all_in_one_computers'),
    path('hardware/fresh_laptops/', views.fresh_laptops, name='fresh_laptops'),
    path('hardware/fresh_desktops/', views.fresh_desktops, name='fresh_desktops'),
    path('hardware/used_laptops/', views.used_laptops, name='used_laptops'),
    path('hardware/used_desktops/', views.used_desktops, name='used_desktops'),
    path('hardware/peripherals/', views.peripherals, name='peripherals'),
    path('hardware/networking/', views.networking_all, name='networking_all'),
    path('hardware/switches/', views.switches, name='switches'),
    path('hardware/routers-and-modems/', views.routers_modems, name='routers_modems'),
    path('hardware/access-points/', views.access_points, name='access_points'),
    path('hardware/ups/', views.ups, name='ups'),
    path('hardware/security-cameras/', views.security_cameras, name='security_cameras'),
    path('hardware/ip-cameras/', views.ip_cameras, name='ip_cameras'),
    path('hardware/cctv-kits/', views.cctv_kits, name='cctv_kits'),
    path('hardware/nvr-dvr/', views.nvr_dvr, name='nvr_dvr'),

    # Navigation software links
    path('software/all/', views.software_all, name='software_all'),
    path('software/operatingSystems/', views.operatingSystems, name='operatingSystems'),
    path('software/applications/', views.applications, name='applications'),
    path('software/office-suite/', views.office_suite, name='office_suite'),
    path('software/design-creative/', views.design_creative, name='design_creative'),
    path('software/accounting-finance/', views.accounting_finance, name='accounting_finance'),
    path('software/video-editing/', views.video_editing, name='video_editing'),
    path('software/point-of-sale/', views.point_of_sale, name='point_of_sale'),
    path('software/security-utilities/', views.security_utilities, name='security_utilities'),
    path('software/antivirus-security/', views.antivirus_security, name='antivirus_security'),
    path('software/remote-desktop-vpn/', views.remote_desktop_vpn, name='remote_desktop_vpn'),
    path('software/backup-recovery/', views.backup_recovery, name='backup_recovery'),
    path('software/network-management/', views.network_management, name='network_management'),
    path('software/developmentTools/', views.developmentTools, name='developmentTools'),
    path('software/development-only/', views.development_tools_only, name='development_tools_only'),
    path('software/database-software/', views.database_software, name='database_software'),

    # Navigation IT solutions links
    path('itSolutions/CCTVInstallation/', views.cctv, name='CCTVInstallation'),
    path('itSolutions/cctvServices/', views.cctvServices, name='cctvServices'),
    path('itSolutions/hardwareRepairs/', views.hardwareRepairs, name='hardwareRepairs'),
    path('itSolutions/hardwareServices/', views.hardwareServices, name='hardwareServices'),
    path('itSolutions/networkingSolutions/', views.networkingSolutions, name='networkingSolutions'),
    path('itSolutions/networkingServices/', views.networkingServices, name='networkingServices'),
   
    # Navigation Research Hub links
    path('research/projects/', views.projects, name='projects'),
    path('research/hardware/', views.hardware, name='hardware'),
    path('research/hadware/', views.hardware, name='hadware'),
    path('research/security/', views.security, name='security'),
    path('research/seurity/', views.security, name='seurity'),
    path('research/networking/', views.networking, name='networking'),
    path('research/ai/', views.ai, name='ai'),
    path('research/cloud/', views.cloud, name='cloud'),
    

    
    
    
    
    
    


    #allproducts#
    path('hardware/allproducts/', views.allproducts, name='allproducts'),
    path('subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),


] 
# Error handlers
handler404 = 'LiG.views.handler404'
handler500 = 'LiG.views.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
