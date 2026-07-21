from django.contrib import admin
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import path

# We'll keep the custom logout view but keep the default admin site
admin.site.site_header = "SKYDEMY Admin"
admin.site.site_title = "SKYDEMY Admin"
admin.site.index_title = "Dashboard"

def admin_logout(request):
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('/admin/login/')

# Add custom logout URL manually in urls.py