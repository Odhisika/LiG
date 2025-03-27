from django.urls import path
from .views import *

urlpatterns = [
    path('', research, name='research'),
    path('add-blog/', add_blog, name="add_blog"),
    # path('research-detail/<slug:slug>/', research_detail, name="research-detail"),
    path('research/<slug:slug>/', research_detail, name='research-detail'),
    path('see-blog/', see_blog, name="see_blog"),
    path('blog-delete/<id>', blog_delete, name="blog_delete"),
    path('blog-update/<slug>/', blog_update, name="blog_update"),
    path('search-blog/', search1, name="search1"),
    
    
]
