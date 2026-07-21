from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings


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


# Create an instance of the custom admin site
admin_site = SKYDEMYAdminSite()

# Also assign to admin.site for backward compatibility
admin.site = admin_site