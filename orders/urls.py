from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    # path('payment', views.payment_instructions_email, name='payment_instructions_email'),
    path('order_complete/<str:order_number>/', views.order_complete, name='order_complete'),
    path('submit-proof/<str:order_number>/', views.submit_proof, name='submit_proof'),
    path('confirm-payment/<int:proof_id>/', views.confirm_payment, name='confirm_payment'),

]
