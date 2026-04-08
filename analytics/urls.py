from django.urls import path
from .dashboard import dashboard_site

urlpatterns = [
    path('', dashboard_site.urls),
]
