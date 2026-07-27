from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('registration-success/', views.registration_success, name='registration_success'),
    path('pending-approval/', views.pending_approval, name='pending_approval'),
]