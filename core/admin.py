from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.views import LoginView
from django.urls import path
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages

class SKYDEMYAdminSite(AdminSite):
    site_header = "SKYDEMY Admin"
    site_title = "SKYDEMY Admin"
    index_title = "Dashboard"

    def login(self, request, extra_context=None):
        return LoginView.as_view(template_name='admin/login.html')(request, extra_context=extra_context)

    def logout(self, request, extra_context=None):
        """Handle logout via GET (for convenience)"""
        auth_logout(request)
        messages.info(request, "You have been logged out.")
        return redirect('/admin/login/')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('logout/', self.logout, name='admin_logout'),
        ]
        return custom_urls + urls

# Replace the default admin site with our custom one
admin.site = SKYDEMYAdminSite()