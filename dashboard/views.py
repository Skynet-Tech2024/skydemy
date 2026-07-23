from users.models import UserProfile, Follow, Wishlist, Message
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from courses.models import Lesson, LessonLike, LessonComment, Progress, Certificate
from django.views.decorators.cache import never_cache
from django.template.loader import get_template
from django.conf import settings
from pathlib import Path
from django.contrib.admin.views.decorators import staff_member_required

def home(request):
    # Always show the public landing page
    return render(request, 'dashboard/landing.html')

@login_required
def dashboard(request):
    user = request.user
    
    # Redirect superusers to the admin panel
    if user.is_superuser:
        return redirect('/admin/')
    
    profile = user.profile
    context = {
        'user': user,
        'profile': profile,
    }
    
    if profile.role == 'teacher':
        # Teacher analytics
        lessons = Lesson.objects.filter(teacher=user).order_by('-created_at')
        
        # Total analytics
        total_views = lessons.aggregate(Sum('views'))['views__sum'] or 0
        total_likes = LessonLike.objects.filter(lesson__in=lessons).count()
        total_comments = LessonComment.objects.filter(lesson__in=lessons).count()
        
        # Per lesson stats
        for lesson in lessons:
            lesson.likes_count = LessonLike.objects.filter(lesson=lesson).count()
            lesson.comments_count = LessonComment.objects.filter(lesson=lesson).count()
        
        context['lessons'] = lessons
        context['total_views'] = total_views
        context['total_likes'] = total_likes
        context['total_comments'] = total_comments
        context['followers_count'] = user.followers.count()
        
        return render(request, 'dashboard/teacher_dashboard.html', context)
    
    else:
        # ----- Learner Dashboard -----
        progress = Progress.objects.filter(user=user).select_related('lesson')
        completed_lessons = progress.filter(completed=True).count()
        certificates = Certificate.objects.filter(user=user)
        certificates_count = certificates.count()
        wishlist_count = Wishlist.objects.filter(user=user).count()
        
        # ----- Recommended Lessons -----
        completed_ids = progress.filter(completed=True).values_list('lesson_id', flat=True)
        in_progress_ids = progress.filter(completed=False).values_list('lesson_id', flat=True)
        wishlist_ids = Wishlist.objects.filter(user=user).values_list('lesson_id', flat=True)
        excluded_ids = set(list(completed_ids) + list(in_progress_ids) + list(wishlist_ids))
        
        recommended = Lesson.objects.filter(
            level=profile.level,
            status='approved'
        ).exclude(
            id__in=excluded_ids
        ).annotate(
            engagement=Count('likes') + Count('comments') + Count('progress')
        ).order_by('-engagement', '-views')[:6]
        
        context['progress'] = progress
        context['completed_count'] = completed_lessons
        context['certificates'] = certificates
        context['certificates_count'] = certificates_count
        context['wishlist_count'] = wishlist_count
        context['recommended'] = recommended
        
        return render(request, 'dashboard/learner_dashboard.html', context)

@login_required
def profile(request):
    user = request.user
    
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    
    profile = user.profile
    
    if request.method == 'POST':
        from users.forms import ProfileUpdateForm
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        from users.forms import ProfileUpdateForm
        form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user': user,
        'profile': profile,
        'form': form,
    }
    return render(request, 'dashboard/profile.html', context)

@login_required
def leaderboard(request):
    top_rating = UserProfile.objects.filter(role='learner').order_by('-rating')[:20]
    top_lessons = UserProfile.objects.filter(role='learner').order_by('-total_lessons_completed')[:20]
    top_certificates = UserProfile.objects.filter(role='learner').annotate(
        cert_count=Count('user__certificate')
    ).order_by('-cert_count')[:20]
    
    context = {
        'top_rating': top_rating,
        'top_lessons': top_lessons,
        'top_certificates': top_certificates,
    }
    return render(request, 'dashboard/leaderboard.html', context)

@login_required
def notifications(request):
    user_notifications = request.user.notifications.all()
    unread = user_notifications.filter(is_read=False)
    if unread.exists():
        unread.update(is_read=True)
    context = {
        'notifications': user_notifications,
        'unread_count': 0,
    }
    return render(request, 'dashboard/notifications.html', context)

def unread_notification_count(request):
    if request.user.is_authenticated:
        count = request.user.notifications.filter(is_read=False).count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})

@login_required
def toggle_follow(request, teacher_id):
    teacher = get_object_or_404(User, id=teacher_id, profile__role='teacher')
    
    if request.user == teacher:
        messages.error(request, "You cannot follow yourself.")
        return redirect('lesson_list')
    
    follow_exists = Follow.objects.filter(follower=request.user, following=teacher).exists()
    
    if follow_exists:
        Follow.objects.filter(follower=request.user, following=teacher).delete()
        messages.success(request, f"You have unfollowed {teacher.username}.")
    else:
        Follow.objects.create(follower=request.user, following=teacher)
        messages.success(request, f"You are now following {teacher.username}!")
    
    return redirect('lesson_list')

@login_required
def toggle_wishlist(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.user.profile.role != 'learner':
        messages.error(request, "Only learners can add lessons to wishlist.")
        return redirect('lesson_list')
    
    wishlist_item = Wishlist.objects.filter(user=request.user, lesson=lesson).first()
    
    if wishlist_item:
        wishlist_item.delete()
        messages.success(request, f'Removed "{lesson.title}" from your wishlist.')
    else:
        Wishlist.objects.create(user=request.user, lesson=lesson)
        messages.success(request, f'Added "{lesson.title}" to your wishlist!')
    
    next_url = request.GET.get('next', 'lesson_list')
    if next_url == 'view_lesson':
        return redirect('view_lesson', lesson_id=lesson.id)
    return redirect('lesson_list')

@login_required
def progress_chart(request):
    if request.user.profile.role != 'learner':
        messages.error(request, 'Only learners can view progress charts.')
        return redirect('dashboard')
    
    from users.models import ProgressHistory
    
    history = ProgressHistory.objects.filter(user=request.user).order_by('recorded_at')
    
    labels = []
    lessons_data = []
    rating_data = []
    
    for entry in history:
        labels.append(entry.recorded_at.strftime('%b %d'))
        lessons_data.append(entry.total_lessons_completed)
        rating_data.append(float(entry.rating))
    
    context = {
        'history': history,
        'labels': labels,
        'lessons_data': lessons_data,
        'rating_data': rating_data,
    }
    return render(request, 'dashboard/progress_chart.html', context)

@login_required
def inbox(request):
    received_messages = Message.objects.filter(receiver=request.user)
    sent_messages = Message.objects.filter(sender=request.user)
    
    unread = received_messages.filter(is_read=False)
    if unread.exists():
        unread.update(is_read=True)
    
    context = {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
    }
    return render(request, 'dashboard/inbox.html', context)

@login_required
def send_message(request):
    if request.method == 'POST':
        receiver_username = request.POST.get('receiver')
        subject = request.POST.get('subject', '')
        content = request.POST.get('content')
        
        if not content:
            messages.error(request, "Message content cannot be empty.")
            return redirect('inbox')
        
        try:
            receiver = User.objects.get(username=receiver_username)
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('inbox')
        
        if receiver == request.user:
            messages.error(request, "You cannot send a message to yourself.")
            return redirect('inbox')
        
        Message.objects.create(
            sender=request.user,
            receiver=receiver,
            subject=subject,
            content=content
        )
        
        from users.utils import create_notification
        create_notification(
            user=receiver,
            notification_type='system',
            title='📩 New Message',
            message=f'You have a new message from {request.user.username}.',
            link='/inbox/'
        )
        
        messages.success(request, f"Message sent to {receiver.username}!")
        return redirect('inbox')
    
    users = User.objects.exclude(id=request.user.id).filter(profile__is_suspended=False)
    return render(request, 'dashboard/send_message.html', {'users': users})

@never_cache
def service_worker(request):
    content = '''
// Service Worker for SKYDEMY PWA
const CACHE_NAME = 'skydemy-v1';
const urlsToCache = [
    '/',
    '/static/images/logo.png',
    '/static/manifest.json'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== CACHE_NAME) {
                        return caches.delete(name);
                    }
                })
            );
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => response || fetch(event.request))
    );
});
'''
    return HttpResponse(content.strip(), content_type='application/javascript')


# ===== DEBUG VIEW =====
def debug_templates(request):
    """Debug view to check template loading and paths."""
    base_dir = settings.BASE_DIR
    templates_path = base_dir / 'templates'
    templates_exists = templates_path.exists()

    admin_template_path = templates_path / 'admin' / 'base_site.html'
    admin_exists = admin_template_path.exists()

    try:
        t = get_template('admin/base_site.html')
        template_loaded = True
        template_origin = t.origin.name
    except Exception as e:
        template_loaded = False
        template_origin = str(e)

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


# ===== STUDENT AND TEACHER LIST VIEWS =====
@staff_member_required
def student_list(request):
    """Admin view to list all students (users with role=learner)."""
    students = UserProfile.objects.filter(role='learner').select_related('user')
    return render(request, 'dashboard/student_list.html', {'students': students})

@staff_member_required
def teacher_list(request):
    """Admin view to list all teachers (users with role=teacher)."""
    teachers = UserProfile.objects.filter(role='teacher').select_related('user')
    return render(request, 'dashboard/teacher_list.html', {'teachers': teachers})