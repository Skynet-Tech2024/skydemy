from django.http import HttpResponse
from pathlib import Path
from django.template.loader import get_template
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages

def admin_logout(request):
    """Custom logout view for admin."""
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('/admin/login/')from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages

def admin_logout(request):
    """Custom logout view for admin."""
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('/admin/login/')from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages

def admin_logout(request):
    """Custom logout view for admin."""
    auth_logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('/admin/login/')

def debug_templates(request):
    """Debug view to check template loading and paths."""
    import os
    from django.conf import settings
    
    # 1. Check BASE_DIR
    base_dir = settings.BASE_DIR
    
    # 2. Check templates folder exists
    templates_path = base_dir / 'templates'
    templates_exists = templates_path.exists()
    
    # 3. Check admin/base_site.html exists
    admin_template_path = templates_path / 'admin' / 'base_site.html'
    admin_exists = admin_template_path.exists()
    
    # 4. Try to load the template via Django
    try:
        t = get_template('admin/base_site.html')
        template_loaded = True
        template_origin = t.origin.name
    except Exception as e:
        template_loaded = False
        template_origin = str(e)
    
    # 5. List files in templates/admin/
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