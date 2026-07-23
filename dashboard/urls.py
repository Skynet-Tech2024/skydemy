from django.urls import path
from . import views
from .views import (
    home, dashboard, profile, leaderboard, notifications,
    unread_notification_count, toggle_follow, toggle_wishlist,
    progress_chart, inbox, send_message, service_worker,
    debug_templates, student_list, teacher_list, batch_student_action
)

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile, name='profile'),
    path('leaderboard/', leaderboard, name='leaderboard'),
    path('notifications/', notifications, name='notifications'),
    path('notifications/unread-count/', unread_notification_count, name='unread_notification_count'),
    path('follow/<int:teacher_id>/', toggle_follow, name='toggle_follow'),
    path('wishlist/<int:lesson_id>/', toggle_wishlist, name='toggle_wishlist'),
    path('progress-chart/', progress_chart, name='progress_chart'),
    path('inbox/', inbox, name='inbox'),
    path('send-message/', send_message, name='send_message'),
    path('sw.js/', service_worker, name='sw.js'),
    path('debug/', debug_templates, name='debug_templates'),
    
    # Admin user lists
    path('students/', student_list, name='student_list'),
    path('teachers/', teacher_list, name='teacher_list'),
    
    # Batch action
    path('students/batch-action/', batch_student_action, name='batch_student_action'),
]