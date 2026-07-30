from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # ===== LESSON VIEWS =====
    path('', views.lesson_list, name='lesson_list'),
    path('upload/', views.upload_lesson, name='upload_lesson'),
    path('add-subject/', views.add_subject, name='add_subject'),

    # ===== LEARNER DASHBOARD =====
    # 👇 MUST come BEFORE lesson/<int:lesson_id>/ to avoid conflicts
    

    # ===== LESSON VIEWER =====
    path('lesson/<int:lesson_id>/', views.view_lesson, name='view_lesson'),
    path('lesson/<int:lesson_id>/convert-whiteboard/', views.convert_lesson_to_whiteboard, name='convert_lesson_to_whiteboard'),

    # ===== EXAM VIEWS =====
    path('lesson/<int:lesson_id>/add-exam/', views.add_exam, name='add_exam'),
    path('lesson/<int:lesson_id>/take-exam/', views.take_exam, name='take_exam'),
    path('exam/result/<int:result_id>/', views.exam_result, name='exam_result'),

    # ===== EXAM MANAGEMENT =====
    path('exams/fslc/add/', views.add_fslc_papers, name='add_fslc_papers'),
    path('exams/mock-primary/add/', views.add_mock_papers_primary, name='add_mock_papers_primary'),
    path('exams/mock/select-level/', views.select_mock_exam_level, name='select_mock_exam_level'),
    path('exams/mock/add/<str:level>/', views.add_mock_exam, name='add_mock_exam'),
    path('exams/gce/select-level/', views.select_gce_level, name='select_gce_level'),
    path('exams/gce/add/<str:level>/', views.add_gce_past_questions, name='add_gce_past_questions'),

    # ===== ADMIN WIZARDS =====
    path('exam/create/', views.create_exam_wizard, name='create_exam_wizard'),
    path('certificate/issue/', views.issue_certificate_wizard, name='issue_certificate_wizard'),
    path('course/create/', views.create_course_wizard, name='create_course_wizard'),

    # ===== API ENDPOINTS =====
    path('api/lesson-progress/', views.save_lesson_progress, name='save_lesson_progress'),
]