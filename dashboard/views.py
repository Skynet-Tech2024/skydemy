from users.models import UserProfile, Follow, Wishlist, Message
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from courses.models import Lesson, LessonLike, LessonComment, Progress, Certificate, Subject, Exam
from django.views.decorators.cache import never_cache
from django.template.loader import get_template
from django.conf import settings
from pathlib import Path
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse

def home(request):
    return render(request, 'dashboard/landing.html')

@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser:
        return redirect('/admin/')
    
    profile = user.profile
    context = {'user': user, 'profile': profile}
    
    if profile.role == 'teacher':
        lessons = Lesson.objects.filter(teacher=user).order_by('-created_at')
        total_views = lessons.aggregate(Sum('views'))['views__sum'] or 0
        total_likes = LessonLike.objects.filter(lesson__in=lessons).count()
        total_comments = LessonComment.objects.filter(lesson__in=lessons).count()
        for lesson in lessons:
            lesson.likes_count = LessonLike.objects.filter(lesson=lesson).count()
            lesson.comments_count = LessonComment.objects.filter(lesson=lesson).count()
        context.update({
            'lessons': lessons,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'followers_count': user.followers.count(),
        })
        return render(request, 'dashboard/teacher_dashboard.html', context)
    else:
        progress = Progress.objects.filter(user=user).select_related('lesson')
        completed_lessons = progress.filter(completed=True).count()
        certificates = Certificate.objects.filter(user=user)
        certificates_count = certificates.count()
        wishlist_count = Wishlist.objects.filter(user=user).count()
        completed_ids = progress.filter(completed=True).values_list('lesson_id', flat=True)
        in_progress_ids = progress.filter(completed=False).values_list('lesson_id', flat=True)
        wishlist_ids = Wishlist.objects.filter(user=user).values_list('lesson_id', flat=True)
        excluded_ids = set(list(completed_ids) + list(in_progress_ids) + list(wishlist_ids))
        recommended = Lesson.objects.filter(
            level=profile.level,
            status='approved'
        ).exclude(id__in=excluded_ids).annotate(
            engagement=Count('likes') + Count('comments') + Count('progress')
        ).order_by('-engagement', '-views')[:6]
        context.update({
            'progress': progress,
            'completed_count': completed_lessons,
            'certificates': certificates,
            'certificates_count': certificates_count,
            'wishlist_count': wishlist_count,
            'recommended': recommended,
        })
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
    return render(request, 'dashboard/profile.html', {'user': user, 'profile': profile, 'form': form})

@login_required
def leaderboard(request):
    top_rating = UserProfile.objects.filter(role='learner').order_by('-rating')[:20]
    top_lessons = UserProfile.objects.filter(role='learner').order_by('-total_lessons_completed')[:20]
    top_certificates = UserProfile.objects.filter(role='learner').annotate(
        cert_count=Count('user__certificate')
    ).order_by('-cert_count')[:20]
    return render(request, 'dashboard/leaderboard.html', {
        'top_rating': top_rating,
        'top_lessons': top_lessons,
        'top_certificates': top_certificates,
    })

@login_required
def notifications(request):
    user_notifications = request.user.notifications.all()
    unread = user_notifications.filter(is_read=False)
    if unread.exists():
        unread.update(is_read=True)
    return render(request, 'dashboard/notifications.html', {
        'notifications': user_notifications,
        'unread_count': 0,
    })

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
    labels = [entry.recorded_at.strftime('%b %d') for entry in history]
    lessons_data = [entry.total_lessons_completed for entry in history]
    rating_data = [float(entry.rating) for entry in history]
    return render(request, 'dashboard/progress_chart.html', {
        'history': history,
        'labels': labels,
        'lessons_data': lessons_data,
        'rating_data': rating_data,
    })

@login_required
def inbox(request):
    received_messages = Message.objects.filter(receiver=request.user)
    sent_messages = Message.objects.filter(sender=request.user)
    unread = received_messages.filter(is_read=False)
    if unread.exists():
        unread.update(is_read=True)
    return render(request, 'dashboard/inbox.html', {
        'received_messages': received_messages,
        'sent_messages': sent_messages,
    })

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

def debug_templates(request):
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
    students = UserProfile.objects.filter(role='learner').select_related('user')
    return render(request, 'dashboard/student_list.html', {'students': students})

@staff_member_required
def teacher_list(request):
    teachers = UserProfile.objects.filter(role='teacher').select_related('user')
    return render(request, 'dashboard/teacher_list.html', {'teachers': teachers})

# ===== BATCH STUDENT ACTION =====
@staff_member_required
def batch_student_action(request):
    if request.method != 'POST':
        return redirect('student_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No students selected.")
        return redirect('student_list')
    profiles = UserProfile.objects.filter(id__in=selected_ids, role='learner')
    if action == 'approve':
        profiles.update(verification_status='approved')
        messages.success(request, f"Approved {profiles.count()} student(s).")
    elif action == 'verify':
        profiles.update(verification_status='verified')
        messages.success(request, f"Verified {profiles.count()} student(s).")
    elif action == 'suspend':
        profiles.update(is_suspended=True)
        messages.success(request, f"Suspended {profiles.count()} student(s).")
    elif action == 'activate':
        profiles.update(is_suspended=False)
        messages.success(request, f"Activated {profiles.count()} student(s).")
    elif action == 'delete':
        user_ids = profiles.values_list('user_id', flat=True)
        count = profiles.count()
        profiles.delete()
        User.objects.filter(id__in=user_ids).delete()
        messages.success(request, f"Deleted {count} student(s).")
    else:
        messages.error(request, "Invalid action.")
    return redirect('student_list')

# ===== BATCH TEACHER ACTION =====
@staff_member_required
def batch_teacher_action(request):
    if request.method != 'POST':
        return redirect('teacher_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No teachers selected.")
        return redirect('teacher_list')
    profiles = UserProfile.objects.filter(id__in=selected_ids, role='teacher')
    if action == 'approve':
        profiles.update(verification_status='approved')
        messages.success(request, f"Approved {profiles.count()} teacher(s).")
    elif action == 'verify':
        profiles.update(verification_status='verified')
        messages.success(request, f"Verified {profiles.count()} teacher(s).")
    elif action == 'suspend':
        profiles.update(is_suspended=True)
        messages.success(request, f"Suspended {profiles.count()} teacher(s).")
    elif action == 'activate':
        profiles.update(is_suspended=False)
        messages.success(request, f"Activated {profiles.count()} teacher(s).")
    elif action == 'delete':
        user_ids = profiles.values_list('user_id', flat=True)
        count = profiles.count()
        profiles.delete()
        User.objects.filter(id__in=user_ids).delete()
        messages.success(request, f"Deleted {count} teacher(s).")
    else:
        messages.error(request, "Invalid action.")
    return redirect('teacher_list')

# ===== SUBJECT LIST VIEW =====
@staff_member_required
def subject_list(request):
    """Admin view to list all subjects with stat cards and batch actions."""
    subjects = Subject.objects.all().order_by('-created_at')
    total_count = subjects.count()
    pending_count = subjects.filter(status='pending').count()
    approved_count = subjects.filter(status='approved').count()
    rejected_count = subjects.filter(status='rejected').count()
    context = {
        'subjects': subjects,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'dashboard/subject_list.html', context)

# ===== BATCH SUBJECT ACTION =====
@staff_member_required
def batch_subject_action(request):
    if request.method != 'POST':
        return redirect('subject_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No subjects selected.")
        return redirect('subject_list')
    queryset = Subject.objects.filter(id__in=selected_ids)
    if action == 'approve_subjects':
        count = queryset.update(status='approved')
        messages.success(request, f"{count} subject(s) approved.")
    elif action == 'reject_subjects':
        count = queryset.update(status='rejected')
        messages.success(request, f"{count} subject(s) rejected.")
    elif action == 'delete_selected_subjects':
        count = queryset.count()
        queryset.delete()
        messages.success(request, f"{count} subject(s) deleted.")
    else:
        messages.error(request, "Invalid action.")
    return redirect('subject_list')

# ===== EXAM LIST VIEW =====
@staff_member_required
def exam_list(request):
    """Admin view to list all exams with stat cards and batch actions."""
    exams = Exam.objects.select_related('lesson').all().order_by('-created_at')
    total_count = exams.count()
    pending_count = exams.filter(status='pending').count()
    approved_count = exams.filter(status='approved').count()
    rejected_count = exams.filter(status='rejected').count()
    context = {
        'exams': exams,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'dashboard/exam_list.html', context)

# ===== BATCH EXAM ACTION =====
@staff_member_required
def batch_exam_action(request):
    if request.method != 'POST':
        return redirect('exam_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No exams selected.")
        return redirect('exam_list')
    queryset = Exam.objects.filter(id__in=selected_ids)
    if action == 'approve_exams':
        count = queryset.update(status='approved')
        messages.success(request, f"{count} exam(s) approved.")
    elif action == 'reject_exams':
        count = queryset.update(status='rejected')
        messages.success(request, f"{count} exam(s) rejected.")
    elif action == 'delete_selected_exams':
        count = queryset.count()
        queryset.delete()
        messages.success(request, f"{count} exam(s) deleted.")
    else:
        messages.error(request, "Invalid action.")
    return redirect('exam_list')