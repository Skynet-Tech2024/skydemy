from django.urls import path
from . import views

urlpatterns = [
    path('', views.lesson_list, name='lesson_list'),
    path('upload/', views.upload_lesson, name='upload_lesson'),
    path('add-subject/', views.add_subject, name='add_subject'),
    path('lesson/<int:lesson_id>/', views.view_lesson, name='view_lesson'),
    path('lesson/<int:lesson_id>/add-exam/', views.add_exam, name='add_exam'),
    path('lesson/<int:lesson_id>/take-exam/', views.take_exam, name='take_exam'),
]