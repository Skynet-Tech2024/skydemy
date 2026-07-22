from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse
from users.views import register, custom_login, custom_logout, complete_profile

# Debug views
def debug_templates(request):
    import os
    from django.template.loader import get_template
    from django.conf import settings
    base_dir = settings.BASE_DIR
    templates_dir = base_dir / 'templates'
    admin_templates_dir = templates_dir / 'admin'
    
    # Check if admin/base_site.html exists
    admin_base_site = admin_templates_dir / 'base_site.html'
    admin_base_site_exists = admin_base_site.exists()
    
    # Try to load the template
    try:
        template = get_template('admin/base_site.html')
        template_loaded = True
        template_origin = template.origin.name if hasattr(template, 'origin') else 'Unknown'
    except Exception as e:
        template_loaded = False
        template_origin = str(e)
    
    # List files in templates/admin/
    files = []
    if admin_templates_dir.exists():
        files = [f.name for f in admin_templates_dir.iterdir() if f.is_file()]
    
    return JsonResponse({
        'BASE_DIR': str(base_dir),
        'templates_folder_exists': templates_dir.exists(),
        'admin_base_site_exists': admin_base_site_exists,
        'template_loaded': template_loaded,
        'template_origin': template_origin,
        'files_in_admin_templates': files,
        'DEBUG': settings.DEBUG,
    })

urlpatterns = [
    # Service worker
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw.js'),
    
    # Captcha
    path('captcha/', include('captcha.urls')),
    
    # Admin
    path('admin/logout/', admin.site.logout, name='admin_logout'),
    path('admin/', admin.site.urls),
    
    # Debug
    path('debug-templates/', debug_templates, name='debug_templates'),
    path('debug/', debug_templates, name='debug_templates'),
    
    # User URLs (direct)
    path('', include('dashboard.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('profile/', include('dashboard.urls')),
    path('leaderboard/', include('dashboard.urls')),
    path('notifications/', include('dashboard.urls')),
    path('notifications/unread-count/', include('dashboard.urls')),
    path('follow/<int:teacher_id>/', include('dashboard.urls')),
    path('wishlist/<int:lesson_id>/', include('dashboard.urls')),
    path('progress-chart/', include('dashboard.urls')),
    path('inbox/', include('dashboard.urls')),
    path('send-message/', include('dashboard.urls')),
    
    # Users
    path('users/register/', register, name='register'),
    path('users/login/', custom_login, name='login'),
    path('users/logout/', custom_logout, name='logout'),
    path('users/complete-profile/', complete_profile, name='complete_profile'),
    
    # Courses
    path('courses/', include('courses.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)