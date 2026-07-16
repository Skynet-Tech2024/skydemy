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

    def login(self, request, extra_context=None):
        from django.contrib.admin.views import LoginView
        return LoginView.as_view(template_name='admin/login.html')(request, extra_context=extra_context)

    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        return app_list

   def index(self, request, extra_context=None):
    import sys
    extra_context = extra_context or {}
    
    student_count = UserProfile.objects.filter(role='learner').count()
    teacher_count = UserProfile.objects.filter(role='teacher').count()
    course_count = Course.objects.count()
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()

    print(f"DEBUG: student_count={student_count}, teacher_count={teacher_count}, course_count={course_count}, exam_count={exam_count}, certificate_count={certificate_count}", file=sys.stderr)

    extra_context['student_count'] = student_count
    extra_context['teacher_count'] = teacher_count
    extra_context['course_count'] = course_count
    extra_context['exam_count'] = exam_count
    extra_context['certificate_count'] = certificate_count
    extra_context['recent_actions'] = LogEntry.objects.select_related('user', 'content_type')[:10]
    return super().index(request, extra_context)course_count={course_count}, exam_count={exam_count}, certificate_count={certificate_count}")

        extra_context['student_count'] = student_count
        extra_context['teacher_count'] = teacher_count
        extra_context['course_count'] = course_count
        extra_context['exam_count'] = exam_count
        extra_context['certificate_count'] = certificate_count
        extra_context['recent_actions'] = LogEntry.objects.select_related('user', 'content_type')[:10]
        return super().index(request, extra_context)

# Replace the default admin site with our custom one
admin.site = SKYDEMYAdminSite()