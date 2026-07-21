from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from django.contrib.admin.views.main import ChangeList

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
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        """
        Override the admin index view to use a custom template with footer.
        """
        context = self.each_context(request)
        context.update(extra_context or {})
        # Add the footer to the context? No, we'll hardcode it in the template.
        return TemplateResponse(
            request,
            'admin/custom_index.html',  # We'll create this template
            context
        )

    def changelist_view(self, request, model_admin, model, **kwargs):
        """
        Override the changelist view to use a custom template with footer.
        """
        # This is more complex; we can handle it by setting a custom template
        # on each ModelAdmin, but for simplicity we'll override the response.
        # We'll instead set a custom template for each model admin that we want.
        # But for now, we'll just override the index and let the change list
        # inherit from the custom base.html.
        return super().changelist_view(request, model_admin, model, **kwargs)

# Replace the default admin site with our custom one
admin_site = SKYDEMYAdminSite()