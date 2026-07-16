from django.contrib import admin
from django.contrib.admin import AdminSite

class SKYDEMYAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def login(self, request, extra_context=None):
        from django.contrib.admin.views import LoginView
        return LoginView.as_view(template_name='admin/login.html')(request, extra_context=extra_context)

# Replace the default admin site with our custom one
admin.site = SKYDEMYAdminSite()