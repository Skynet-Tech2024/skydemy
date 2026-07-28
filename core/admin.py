from django.contrib.admin import AdminSite
from django.shortcuts import render
from courses.models import Lesson

# ====== Custom Admin Site ======
class SkydemyAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
    lessons = []
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            lessons = Lesson.objects.filter(teacher=request.user).order_by('-created_at')
        elif request.user.is_superuser:
            lessons = Lesson.objects.all().order_by('-created_at')

    total_lessons = Lesson.objects.count()  # <-- ADDED

    context = {
        **self.each_context(request),
        'lessons': lessons,
        'total_lessons': total_lessons,    # <-- ADDED
    }
    if extra_context:
        context.update(extra_context)
    return render(request, 'admin/index.html', context)


# ====== Instantiate the custom admin site ======
admin_site = SkydemyAdminSite()
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
User = get_user_model()
admin_site.register(User, UserAdmin)