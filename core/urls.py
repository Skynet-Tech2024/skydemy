from . import views as core_views
from dashboard.views import service_worker
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .admin import admin_site  # Import the custom admin site

urlpatterns = [
    path('sw.js', service_worker),
    path('captcha/', include('captcha.urls')),
    path('admin/logout/', core_views.admin_logout, name='admin_logout'),
    path('admin/', admin_site.urls),  # Use the custom admin site
    path('debug-templates/', core_views.debug_templates, name='debug_templates'),  # Debug view
    path('', include('dashboard.urls')),
    from users.views import register, custom_login, custom_logout, complete_profile

path('users/register/', register, name='register'),
path('users/login/', custom_login, name='login'),
path('users/logout/', custom_logout, name='logout'),
path('users/complete-profile/', complete_profile, name='complete_profile'),
    path('courses/', include('courses.urls')),
]

# Serve static and media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)