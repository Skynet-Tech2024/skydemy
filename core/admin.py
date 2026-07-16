from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User
from courses.models import Course, Exam, Certificate
from users.models import UserProfile
from django.contrib.admin.models import LogEntry

class SKYDEMYAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def get_app_list(self, request):
        # This is the default app list
        app_list = super().get_app_list(request)
        return app_list

    def index(self, request, extra_context=None):
        # Add statistics to the context
        extra_context = extra_context or {}
        extra_context['student_count'] = UserProfile.objects.filter(role='learner').count()
        extra_context['course_count'] = Course.objects.count()
        extra_context['exam_count'] = Exam.objects.count()
        extra_context['certificate_count'] = Certificate.objects.count()
        extra_context['recent_actions'] = LogEntry.objects.select_related('user', 'content_type')[:10]
        return super().index(request, extra_context)

# Replace the default admin site with our custom one
admin.site = SKYDEMYAdminSite()