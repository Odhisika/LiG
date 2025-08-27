from django.urls import path
from . import views

# Remove app_name to avoid namespacing
urlpatterns = [
    path('initialize/<int:order_id>/', views.initialize_payment, name='initialize_payment'),
    path('verify/', views.verify_payment, name='verify_payment'),
    path('webhook/', views.paystack_webhook, name='paystack_webhook'),
    path('status/<int:payment_id>/', views.payment_status, name='payment_status'),
    path('detail/<int:payment_id>/', views.payment_detail, name='payment_detail'),
]