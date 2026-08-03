from django.urls import path
from . import views
from .views import (
    home, dashboard, profile, leaderboard, notifications,
    unread_notification_count, toggle_follow, toggle_wishlist,
    progress_chart, inbox, send_message, service_worker,
    debug_templates, student_list, teacher_list, batch_student_action,
    batch_teacher_action, subject_list, batch_subject_action,
    exam_list, batch_exam_action,
    certificate_list, batch_certificate_action,
    course_list, batch_course_action,
    examresult_list, batch_examresult_action,
    lesson_list, batch_lesson_action
)

urlpatterns = [
    # Main pages
path('reset-cycle/', views.reset_cycle, name='reset_cycle'),
path('debug-cycle/', views.debug_cycle, name='debug_cycle'),    
path('', home, name='home'),
    path('dashboard/', dashboard, name='dashboard'),
    path('profile/', profile, name='profile'),
# Admin withdrawal management
path('admin/withdrawals/', views.admin_withdrawal_requests, name='admin_withdrawal_requests'),
path('admin/withdrawals/<int:pk>/', views.admin_withdrawal_detail, name='admin_withdrawal_detail'),
path('admin/withdrawals/<int:pk>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
path('admin/withdrawals/<int:pk>/reject/', views.reject_withdrawal, name='reject_withdrawal'),
path('request-withdrawal/', views.request_withdrawal, name='request_withdrawal'),
path('subjects/batch-action/', views.batch_subject_action, name='batch_subject_action'),    
path('leaderboard/', leaderboard, name='leaderboard'),

    # Subjects
    path('subjects/', subject_list, name='subject_list'),
    path('batch-subject-action/', batch_subject_action, name='batch_subject_action'),

    # Exams
    path('exams/', exam_list, name='exam_list'),
    path('batch-exam-action/', batch_exam_action, name='batch_exam_action'),

    # Certificates
    path('certificates/', certificate_list, name='certificate_list'),
    path('batch-certificate-action/', batch_certificate_action, name='batch_certificate_action'),

    # Courses
    path('courses/', course_list, name='course_list'),
    path('batch-course-action/', batch_course_action, name='batch_course_action'),

    # Exam Results
    path('examresults/', examresult_list, name='examresult_list'),
    path('batch-examresult-action/', batch_examresult_action, name='batch_examresult_action'),

    # Lessons
    path('lessons/', lesson_list, name='lesson_list'),
    path('batch-lesson-action/', batch_lesson_action, name='batch_lesson_action'),

    # Notifications
    path('notifications/', notifications, name='notifications'),
    path('notifications/unread-count/', unread_notification_count, name='unread_notification_count'),

    # Social features
    path('follow/<int:teacher_id>/', toggle_follow, name='toggle_follow'),
    path('wishlist/<int:lesson_id>/', toggle_wishlist, name='toggle_wishlist'),

    # Progress & messaging
    path('progress-chart/', progress_chart, name='progress_chart'),
    path('inbox/', inbox, name='inbox'),
    path('send-message/', send_message, name='send_message'),

    # Service worker & debug
    path('sw.js/', service_worker, name='sw.js'),
    path('debug/', debug_templates, name='debug_templates'),

    # Admin user lists
    path('students/', student_list, name='student_list'),
    path('teachers/', teacher_list, name='teacher_list'),

    # Batch actions
    path('students/batch-action/', batch_student_action, name='batch_student_action'),
    path('teachers/batch-action/', batch_teacher_action, name='batch_teacher_action'),
]