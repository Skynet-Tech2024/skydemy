from django.urls import path
from . import views
from .views import register, custom_login, custom_logout, complete_profile

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
path('complete-profile/', complete_profile, name='complete_profile'),
]