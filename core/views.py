from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages

def admin_logout(request):
    """Custom logout view for admin."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('/admin/login/')