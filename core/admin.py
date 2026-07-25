from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.utils import timezone
from django.db.models import Count

# Import models for statistics
from courses.models import Course, Lesson, Exam, ExamResult, Certificate
from users.models import UserProfile, Activity
from django.contrib.auth.models import User  # <-- ADDED


class SKYDEMYAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def logout(self, request, extra_context=None):
        auth_logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('/admin/login/')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('logout/', self.logout, name='admin_logout'),
            path('debug/', self.debug_templates, name='admin_debug'),
        ]
        return custom_urls + urls

    def debug_templates(self, request):
        from pathlib import Path
        base_dir = settings.BASE_DIR
        templates_path = base_dir / 'templates'
        templates_exists = templates_path.exists()
        admin_template_path = templates_path / 'admin' / 'base_site.html'
        admin_exists = admin_template_path.exists()
        try:
            t = get_template('admin/base_site.html')
            template_loaded = True
            template_origin = t.origin.name
        except Exception as e:
            template_loaded = False
            template_origin = str(e)
        files = []
        if templates_exists:
            admin_dir = templates_path / 'admin'
            if admin_dir.exists():
                files = [f.name for f in admin_dir.iterdir() if f.is_file()]
        response = f"""
        <h1>Debug Template Info</h1>
        <p><strong>BASE_DIR:</strong> {base_dir}</p>
        <p><strong>templates folder exists?</strong> {templates_exists}</p>
        <p><strong>admin/base_site.html exists?</strong> {admin_exists}</p>
        <p><strong>Template loaded via get_template?</strong> {template_loaded}</p>
        <p><strong>Template origin:</strong> {template_origin}</p>
        <p><strong>Files in templates/admin/:</strong> {', '.join(files) if files else 'None'}</p>
        <p><strong>DEBUG:</strong> {settings.DEBUG}</p>
        """
        return HttpResponse(response)

    def index(self, request, extra_context=None):
        """
        Override the default admin index to add statistics, charts data,
        and recent activities context for the dashboard.
        """
        extra_context = extra_context or {}

        # ===== STATISTICS COUNTS =====
        extra_context['total_students'] = UserProfile.objects.filter(role='learner').count()
        extra_context['total_teachers'] = UserProfile.objects.filter(role='teacher').count()
        extra_context['total_courses'] = Course.objects.count()
        extra_context['total_lessons'] = Lesson.objects.count()
        extra_context['total_exams'] = Exam.objects.count()
        extra_context['total_certificates'] = Certificate.objects.count()

        today = timezone.now().date()
        extra_context['active_today'] = UserProfile.objects.filter(
            user__last_login__date=today
        ).count()

        # ===== CHART DATA =====
        extra_context['student_chart_data'] = [5, 10, 15, 20, 25, 30, 35]

        total_lessons = Lesson.objects.count()
        if total_lessons > 0:
            completed = Lesson.objects.filter(progress__completed=True).distinct().count()
            in_progress = Lesson.objects.filter(progress__completed=False).distinct().count()
            not_started = total_lessons - (completed + in_progress)
            extra_context['completion_data'] = [completed, in_progress, not_started]
        else:
            extra_context['completion_data'] = [0, 0, 100]

        # ===== RECENT ACTIVITIES (REAL DATA) =====
        recent_activities = Activity.objects.select_related('user').all()[:15]

        formatted_activities = []
        for activity in recent_activities:
            icon_map = {
                'user_registered': ('fa-user-plus', 'green'),
                'user_logged_in': ('fa-sign-in-alt', 'blue'),
                'course_created': ('fa-plus-circle', 'blue'),
                'lesson_uploaded': ('fa-upload', 'gold'),
                'exam_created': ('fa-file-alt', 'purple'),
                'certificate_issued': ('fa-award', 'orange'),
                'lesson_completed': ('fa-check-circle', 'green'),
                'exam_passed': ('fa-star', 'gold'),
            }
            icon, color = icon_map.get(activity.action, ('fa-circle', 'gray'))

            formatted_activities.append({
                'user': activity.user,
                'username': activity.user.username if activity.user else 'System',
                'action_display': activity.get_action_display(),
                'description': activity.description,
                'link': activity.link,
                'icon': icon,
                'color': color,
                'time_ago': self._time_ago(activity.created_at),
                'created_at': activity.created_at,
            })

        extra_context['recent_activities'] = formatted_activities

        return super().index(request, extra_context)

    def _time_ago(self, dt):
        """Convert datetime to human-readable 'X minutes ago' format."""
        now = timezone.now()
        diff = now - dt
        seconds = diff.total_seconds()

        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f"{days} day{'s' if days > 1 else ''} ago"
        else:
            return dt.strftime("%b %d, %Y")


# ===== Register User Admin for autocomplete =====
class UserAdmin(admin.ModelAdmin):
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active')
    list_filter = ('is_active',)


# Create an instance of the custom admin site
admin_site = SKYDEMYAdminSite()

# Register models with the custom admin site
admin_site.register(User, UserAdmin)  # <-- ADDED

# Also assign to admin.site for backward compatibility
admin.site = admin_site