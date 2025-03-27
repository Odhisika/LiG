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

urlpatterns = [
    # path('admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    path('securelogin/', admin.site.urls),
    path('', views.home, name='home'),
    path('store/', include('store.urls')),
    path('cart/', include('cart.urls')),
    path('accounts/', include('accounts.urls')),
    path('froala_editor/',include('froala_editor.urls')),
    path('research/', include('research.urls')),    

    # ORDERS
    path('orders/', include('orders.urls')),

    # Navigation hardware links
    path('hardware/desktops/', views.desktops, name='desktops'),
    path('hardware/laptops/', views.laptops, name='laptops'),
    path('hardware/peripherals/', views.peripherals, name='peripherals'),

    # Navigation software links
    path('software/operatingSystems/', views.operatingSystems, name='operatingSystems'),
    path('software/applications/', views.applications, name='applications'),
    path('software/developmentTools/', views.developmentTools, name='developmentTools'),

    # Navigation IT solutions links
    path('itSolutions/CCTVInstallation/', views.cctv, name='CCTVInstallation'),
    path('itSolutions/cctvServices/', views.cctvServices, name='cctvServices'),
    path('itSolutions/hardwareRepairs/', views.hardwareRepairs, name='hardwareRepairs'),
    path('itSolutions/hardwareServices/', views.hardwareServices, name='hardwareServices'),
    path('itSolutions/networkingSolutions/', views.networkingSolutions, name='networkingSolutions'),
    path('itSolutions/networkingServices/', views.networkingServices, name='networkingServices'),
   
    # Navigation Research Hub links
    path('research/projects/', views.projects, name='projects'),
    path('research/hadware/', views.hadware, name='hadware'),
    path('research/security/', views.seurity, name='security'),
    path('research/networking/', views.networking, name='networking'),
    path('research/ai/', views.ai, name='ai'),
    path('research/cloud/', views.cloud, name='cloud'),
    

    
    
    
    
    
    


    #allproducts#
    path('hardware/allproducts/', views.allproducts, name='allproducts'),


] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    

