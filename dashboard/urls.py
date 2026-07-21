from django.urls import path
from . import views

urlpatterns = [
path('debug/', views.debug_templates, name='debug_templates'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/unread-count/', views.unread_notification_count, name='unread_notification_count'),
    path('follow/<int:teacher_id>/', views.toggle_follow, name='toggle_follow'),
    path('wishlist/<int:lesson_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('progress-chart/', views.progress_chart, name='progress_chart'),
    path('inbox/', views.inbox, name='inbox'),
    path('send-message/', views.send_message, name='send_message'),
]