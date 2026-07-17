from django.urls import path
from . import views

urlpatterns = [
    path('', views.lesson_list, name='lesson_list'),
    path('upload/', views.upload_lesson, name='upload_lesson'),
    path('add-subject/', views.add_subject, name='add_subject'),
    path('lesson/<int:lesson_id>/', views.view_lesson, name='view_lesson'),
    # Exam management URLs for teachers
    path('exams/fslc/add/', views.add_fslc_papers, name='add_fslc_papers'),
    path('exams/mock-primary/add/', views.add_mock_papers_primary, name='add_mock_papers_primary'),
    path('exams/mock/select-level/', views.select_mock_exam_level, name='select_mock_exam_level'),
    path('exams/mock/add/<str:level>/', views.add_mock_exam, name='add_mock_exam'),
    path('exams/gce/select-level/', views.select_gce_level, name='select_gce_level'),
    path('exams/gce/add/<str:level>/', views.add_gce_past_questions, name='add_gce_past_questions'),
    path('lesson/<int:lesson_id>/add-exam/', views.add_exam, name='add_exam'),
    path('lesson/<int:lesson_id>/take-exam/', views.take_exam, name='take_exam'),
]