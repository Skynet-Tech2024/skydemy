from django.urls import resolve
from django.shortcuts import get_object_or_404
from courses.models import Lesson, Subject, Course

def breadcrumbs(request):
    """
    Build breadcrumb navigation based on the current URL path.
    Returns a list of dicts with 'name' and 'url' keys.
    """
    path = request.path
    breadcrumbs = []
    
    # Always start with Home
    breadcrumbs.append({'name': '🏠 Home', 'url': '/'})
    
    # Match URL patterns and build breadcrumbs
    if path == '/':
        pass  # Already on home
    
    elif path.startswith('/dashboard/'):
        breadcrumbs.append({'name': '📊 Dashboard', 'url': '/dashboard/'})
    
    elif path.startswith('/profile/'):
        breadcrumbs.append({'name': '👤 Profile', 'url': '/profile/'})
    
    elif path.startswith('/courses/upload/'):
        breadcrumbs.append({'name': '📚 Lessons', 'url': '/courses/'})
        breadcrumbs.append({'name': '📤 Upload Lesson', 'url': path})
    
    elif path.startswith('/courses/add-subject/'):
        breadcrumbs.append({'name': '📚 Lessons', 'url': '/courses/'})
        breadcrumbs.append({'name': '➕ Add Subject', 'url': path})
    
    elif path.startswith('/courses/lesson/'):
        # Extract lesson ID
        parts = path.split('/')
        try:
            lesson_id = int(parts[3])
            lesson = get_object_or_404(Lesson, id=lesson_id)
            breadcrumbs.append({'name': '📚 Lessons', 'url': '/courses/'})
            
            # Check if it's add-exam or take-exam
            if len(parts) > 4:
                if parts[4] == 'add-exam':
                    breadcrumbs.append({'name': lesson.title, 'url': f'/courses/lesson/{lesson_id}/'})
                    breadcrumbs.append({'name': '📝 Add Exam', 'url': path})
                elif parts[4] == 'take-exam':
                    breadcrumbs.append({'name': lesson.title, 'url': f'/courses/lesson/{lesson_id}/'})
                    breadcrumbs.append({'name': '📝 Take Exam', 'url': path})
                else:
                    breadcrumbs.append({'name': lesson.title, 'url': path})
            else:
                breadcrumbs.append({'name': lesson.title, 'url': path})
        except (ValueError, IndexError):
            breadcrumbs.append({'name': '📚 Lessons', 'url': '/courses/'})
            breadcrumbs.append({'name': 'Lesson', 'url': path})
    
    elif path.startswith('/courses/'):
        breadcrumbs.append({'name': '📚 All Lessons', 'url': '/courses/'})
    
    elif path.startswith('/users/register/'):
        breadcrumbs.append({'name': '📝 Register', 'url': path})
    
    elif path.startswith('/users/login/'):
        breadcrumbs.append({'name': '🔑 Login', 'url': path})
    
    elif path.startswith('/admin/'):
        breadcrumbs = []  # No breadcrumbs in admin
        breadcrumbs.append({'name': '🔒 Admin', 'url': '/admin/'})
    
    return {'breadcrumbs': breadcrumbs}