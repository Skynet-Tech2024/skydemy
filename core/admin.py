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
from users.models import UserProfile


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
            path('debug/', self.debug_templates, name='admin_debug'),  # Debug view
        ]
        return custom_urls + urls

    def debug_templates(self, request):
        """Debug view to check template loading and paths."""
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
        and quick actions context for the dashboard.
        """
        extra_context = extra_context or {}

        # ===== STATISTICS COUNTS =====
        # Student and teacher counts
        extra_context['total_students'] = UserProfile.objects.filter(role='learner').count()
        extra_context['total_teachers'] = UserProfile.objects.filter(role='teacher').count()

        # Course and lesson counts
        extra_context['total_courses'] = Course.objects.count()
        extra_context['total_lessons'] = Lesson.objects.count()

        # Exam and certificate counts
        extra_context['total_exams'] = Exam.objects.count()
        extra_context['total_certificates'] = Certificate.objects.count()

        # Active today (users who logged in today)
        today = timezone.now().date()
        extra_context['active_today'] = UserProfile.objects.filter(
            user__last_login__date=today
        ).count()

        # ===== CHART DATA (sample – replace with real data later) =====
        # Student registrations over time (last 6 months)
        extra_context['student_chart_data'] = [5, 10, 15, 20, 25, 30, 35]

        # Course completion breakdown (sample)
        total_lessons = Lesson.objects.count()
        if total_lessons > 0:
            # For demo: completed, in-progress, not-started
            completed = Lesson.objects.filter(progress__completed=True).distinct().count()
            in_progress = Lesson.objects.filter(progress__completed=False).distinct().count()
            not_started = total_lessons - (completed + in_progress)
            extra_context['completion_data'] = [completed, in_progress, not_started]
        else:
            extra_context['completion_data'] = [0, 0, 100]

        # ===== RECENT ACTIVITIES (sample – replace with real data later) =====
        extra_context['recent_activities'] = [
            {'user': 'John Doe', 'action': 'enrolled in Mathematics', 'time': '2 minutes ago'},
            {'user': 'Jane Smith', 'action': 'uploaded Algebra Lesson', 'time': '15 minutes ago'},
            {'user': 'Peter Pan', 'action': 'completed HTML Course', 'time': '1 hour ago'},
            {'user': 'Mary Jane', 'action': 'created a new exam', 'time': '3 hours ago'},
        ]

        return super().index(request, extra_context)


# Create an instance of the custom admin site
admin_site = SKYDEMYAdminSite()

# Also assign to admin.site for backward compatibility
admin.site = admin_site