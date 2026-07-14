from dashboard.views import service_worker
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('captcha/', include('captcha.urls')),  # <-- Add this line
path('sw.js', service_worker),    
path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('users/', include('users.urls')),
    path('courses/', include('courses.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)