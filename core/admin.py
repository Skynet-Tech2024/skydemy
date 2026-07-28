from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from courses.models import Lesson

User = get_user_model()

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

        total_lessons = Lesson.objects.count()

        context = {
            **self.each_context(request),
            'lessons': lessons,
            'total_lessons': total_lessons,
        }
        if extra_context:
            context.update(extra_context)
        return render(request, 'admin/index.html', context)


# ====== Instantiate the custom admin site ======
admin_site = SkydemyAdminSite()

# Register the User model with the custom admin site
admin_site.register(User, UserAdmin)