from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.contrib.auth import get_user_model
from courses.models import Lesson

# ====== Custom Admin Site ======
class SkydemyAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        # Fetch lessons for the current user (if teacher or superuser)
        lessons = []
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
                lessons = Lesson.objects.filter(teacher=request.user).order_by('-created_at')
            elif request.user.is_superuser:
                lessons = Lesson.objects.all().order_by('-created_at')

        context = {
            **self.each_context(request),
            'lessons': lessons,
        }
        if extra_context:
            context.update(extra_context)
        return render(request, 'admin/index.html', context)


# ====== Instantiate the custom admin site ======
admin_site = SkydemyAdminSite()


# ====== Import your models and admin classes ======
from courses.models import Subject, Course, Lesson, Progress, Exam, ExamResult, Certificate
from courses.admin import (
    SubjectAdmin,
    CourseAdmin,
    LessonAdmin,
    ProgressAdmin,
    ExamAdmin,
    ExamResultAdmin,
    CertificateAdmin,
)

# ====== Register all models with the custom admin site ======
admin_site.register(Subject, SubjectAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Progress, ProgressAdmin)
admin_site.register(Exam, ExamAdmin)
admin_site.register(ExamResult, ExamResultAdmin)
admin_site.register(Certificate, CertificateAdmin)