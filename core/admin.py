from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.urls import path
from courses.models import Lesson, Subject, Course, Exam, Certificate
from users.models import UserProfile, Level
from users.admin import LevelAdmin
from users.views import admin_level_list  # <-- import the custom view
from datetime import datetime, timedelta
from courses.views import admin_lesson_list

User = get_user_model()

class SkydemyAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def get_urls(self):
        """Add custom admin URLs before the default ones."""
        urls = super().get_urls()
        custom_urls = [
            path('courses/lesson/', self.admin_view(admin_lesson_list), name='lesson_list'),
            path('users/level/', self.admin_view(admin_level_list), name='level_list'),  # <-- new
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        # ----- MY LESSONS (for teacher dashboard) -----
        lessons = []
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
                lessons = Lesson.objects.filter(teacher=request.user).order_by('-created_at')
            elif request.user.is_superuser:
                lessons = Lesson.objects.all().order_by('-created_at')

        # ----- STAT COUNTS -----
        total_students = UserProfile.objects.filter(role='learner').count()
        total_teachers = UserProfile.objects.filter(role='teacher').count()
        total_courses = Course.objects.count()
        total_exams = Exam.objects.count()
        total_certificates = Certificate.objects.count()
        total_lessons = Lesson.objects.count()
        total_subjects = Subject.objects.count()
        total_levels = Level.objects.count()

        # Active Today: users who logged in within the last 24 hours
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        active_today = User.objects.filter(last_login__gte=yesterday).count()

        context = {
            **self.each_context(request),
            'lessons': lessons,
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_courses': total_courses,
            'total_exams': total_exams,
            'total_certificates': total_certificates,
            'total_lessons': total_lessons,
            'total_subjects': total_subjects,
            'total_levels': total_levels,
            'active_today': active_today,
        }
        if extra_context:
            context.update(extra_context)
        return render(request, 'admin/index.html', context)


admin_site = SkydemyAdminSite()

# Register models with the custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Level, LevelAdmin)

# If you want to register other models with their custom admin classes, uncomment and adjust:
# admin_site.register(Course, CourseAdmin)
# admin_site.register(Exam, ExamAdmin)
# admin_site.register(Certificate, CertificateAdmin)
# admin_site.register(Subject, SubjectAdmin)
# Note: Lesson is intentionally NOT registered here because we use the custom view.