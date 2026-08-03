from users.models import UserProfile, Follow, SavedLesson as Wishlist, Message
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from courses.models import TeacherWallet, EarningsCycle, WithdrawalRequest
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from courses.models import TeacherWallet, EarningsCycle, WithdrawalRequest
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.models import User
from courses.models import Lesson, LessonLike, LessonComment, Progress, Certificate, Subject, Exam, Course
from django.views.decorators.cache import never_cache
from django.template.loader import get_template
from django.conf import settings
from pathlib import Path
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from datetime import datetime
from users.utils import create_notification

def home(request):
    return render(request, 'dashboard/landing.html')


@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser:
        return redirect('/admin/')
    
    profile = user.profile
    
    # ===== REFERRAL COUNT =====
    referrals_count = profile.referrals.count()
    
    context = {'user': user, 'profile': profile, 'referrals_count': referrals_count}
    
    if profile.role == 'teacher':
        lessons = Lesson.objects.filter(teacher=user).order_by('-created_at')
        total_views = lessons.aggregate(Sum('views'))['views__sum'] or 0
        total_likes = LessonLike.objects.filter(lesson__in=lessons).count()
        total_comments = LessonComment.objects.filter(lesson__in=lessons).count()
        for lesson in lessons:
            lesson.likes_count = LessonLike.objects.filter(lesson=lesson).count()
            lesson.comments_count = LessonComment.objects.filter(lesson=lesson).count()
        
        # ===== TEACHER EARNINGS DATA =====
        wallet = TeacherWallet.objects.filter(teacher=user).first()
        if not wallet:
            wallet = TeacherWallet.objects.create(teacher=user)

        # Get the current pending/eligible earnings cycle
        current_cycle = EarningsCycle.objects.filter(
            teacher=user,
            status__in=['pending', 'eligible']
        ).first()

        # Get recent completed cycles (last 5)
        recent_cycles = EarningsCycle.objects.filter(
            teacher=user,
            status__in=['claimed', 'paid']
        ).order_by('-completed_at')[:5]

        # Calculate progress toward next payout
        lessons_progress = current_cycle.approved_lessons if current_cycle else 0
        exams_progress = current_cycle.approved_exams if current_cycle else 0
        lessons_needed = max(0, 5 - lessons_progress)
        exams_needed = max(0, 3 - exams_progress)
        cycle_complete = lessons_progress >= 5 and exams_progress >= 3
        next_reward = 5000

        context.update({
            'lessons': lessons,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'followers_count': user.followers.count(),
            # Earnings data
            'wallet': wallet,
            'current_cycle': current_cycle,
            'recent_cycles': recent_cycles,
            'lessons_progress': lessons_progress,
            'exams_progress': exams_progress,
            'lessons_needed': lessons_needed,
            'exams_needed': exams_needed,
            'cycle_complete': cycle_complete,
            'next_reward': next_reward,
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
        
        # Get learner's levels
        learner_levels = profile.levels.all()
        level_codes = [level.code for level in learner_levels] if learner_levels.exists() else []
        
        recommended = Lesson.objects.filter(
            status='approved'
        ).exclude(id__in=excluded_ids)
        
        # Filter by learner's levels if they have any
        if level_codes:
            recommended = recommended.filter(level__in=level_codes)
        
        recommended = recommended.annotate(
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
def request_withdrawal(request):
    """Teacher withdrawal request page."""
    user = request.user
    
    # Check if user is a teacher
    if not hasattr(user, 'profile') or user.profile.role != 'teacher':
        messages.error(request, "Only teachers can request withdrawals.")
        return redirect('dashboard')
    
    # Get or create wallet
    wallet, created = TeacherWallet.objects.get_or_create(teacher=user)
    
    # Check if balance is sufficient
    if wallet.available_balance < 5000:
        messages.error(request, "You need at least 5,000 FCFA to request a withdrawal.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        account_name = request.POST.get('account_name')
        account_number = request.POST.get('account_number')
        confirm = request.POST.get('confirm')
        
        # Validate
        if not all([payment_method, account_name, account_number]):
            messages.error(request, "All fields are required.")
            return render(request, 'dashboard/request_withdrawal.html', {'wallet': wallet})
        
        if payment_method not in ['mtn', 'orange']:
            messages.error(request, "Invalid payment method.")
            return render(request, 'dashboard/request_withdrawal.html', {'wallet': wallet})
        
        if not confirm:
            messages.error(request, "Please confirm your account details.")
            return render(request, 'dashboard/request_withdrawal.html', {'wallet': wallet})
        
        # Find an eligible earnings cycle to claim
        cycle = EarningsCycle.objects.filter(
            teacher=user,
            status='eligible'
        ).first()
        
        if not cycle:
            messages.error(request, "No eligible earnings found. Please complete more lessons and exams.")
            return redirect('dashboard')
        
        # Create withdrawal request
        withdrawal = WithdrawalRequest.objects.create(
            teacher=user,
            amount=5000,
            payment_method=payment_method,
            account_name=account_name,
            account_number=account_number,
            status='pending'
        )
        
        # Mark cycle as claimed
        cycle.status = 'claimed'
        cycle.save()
        
        messages.success(request, "✅ Withdrawal request submitted successfully! Your request is under review. Payment is usually processed within 1–3 business days.")
        return redirect('dashboard')
    
    # GET request - show the form
    return render(request, 'dashboard/request_withdrawal.html', {'wallet': wallet})


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
    """Admin view to list all students with stat cards and filters."""
    students = UserProfile.objects.filter(role='learner').select_related('user')
    
    # Get filter from URL
    status_filter = request.GET.get('status', 'all')
    current_filter = status_filter
    
    # Apply filters
    if status_filter == 'pending':
        students = students.filter(verification_status='pending', is_suspended=False)
    elif status_filter == 'approved':
        students = students.filter(verification_status='approved', is_suspended=False)
    elif status_filter == 'verified':
        students = students.filter(verification_status='verified', is_suspended=False)
    elif status_filter == 'suspended':
        students = students.filter(is_suspended=True)
    elif status_filter == 'active':
        students = students.filter(is_suspended=False)
    # 'all' shows everything
    
    # Counts for stat cards
    total_count = UserProfile.objects.filter(role='learner').count()
    pending_count = UserProfile.objects.filter(role='learner', verification_status='pending', is_suspended=False).count()
    approved_count = UserProfile.objects.filter(role='learner', verification_status='approved', is_suspended=False).count()
    verified_count = UserProfile.objects.filter(role='learner', verification_status='verified', is_suspended=False).count()
    suspended_count = UserProfile.objects.filter(role='learner', is_suspended=True).count()
    active_count = UserProfile.objects.filter(role='learner', is_suspended=False).count()
    
    context = {
        'students': students,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'verified_count': verified_count,
        'suspended_count': suspended_count,
        'active_count': active_count,
        'current_filter': current_filter,
    }
    return render(request, 'dashboard/student_list.html', context)


@staff_member_required
def teacher_list(request):
    """Admin view to list all teachers with stat cards and filters."""
    teachers = UserProfile.objects.filter(role='teacher').select_related('user')
    
    # Get filter from URL
    status_filter = request.GET.get('status', 'all')
    current_filter = status_filter
    
    # Apply filters
    if status_filter == 'pending':
        teachers = teachers.filter(verification_status='pending', is_suspended=False)
    elif status_filter == 'approved':
        teachers = teachers.filter(verification_status='approved', is_suspended=False)
    elif status_filter == 'verified':
        teachers = teachers.filter(verification_status='verified', is_suspended=False)
    elif status_filter == 'suspended':
        teachers = teachers.filter(is_suspended=True)
    # 'all' shows everything
    
    # Counts for stat cards
    total_count = UserProfile.objects.filter(role='teacher').count()
    pending_count = UserProfile.objects.filter(role='teacher', verification_status='pending', is_suspended=False).count()
    approved_count = UserProfile.objects.filter(role='teacher', verification_status='approved', is_suspended=False).count()
    verified_count = UserProfile.objects.filter(role='teacher', verification_status='verified', is_suspended=False).count()
    suspended_count = UserProfile.objects.filter(role='teacher', is_suspended=True).count()
    
    context = {
        'teachers': teachers,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'verified_count': verified_count,
        'suspended_count': suspended_count,
        'current_filter': current_filter,
    }
    return render(request, 'dashboard/teacher_list.html', context)


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
    """Admin view to list all subjects with stat cards and filters."""
    subjects = Subject.objects.all().order_by('-created_at')
    
    # Get filter from URL
    status_filter = request.GET.get('status', 'all')
    current_filter = status_filter
    
    # Apply filters
    if status_filter == 'pending':
        subjects = subjects.filter(status='pending')
    elif status_filter == 'approved':
        subjects = subjects.filter(status='approved')
    elif status_filter == 'rejected':
        subjects = subjects.filter(status='rejected')
    # 'all' shows everything (no filter)
    
    # Counts for stat cards
    total_count = Subject.objects.count()
    pending_count = Subject.objects.filter(status='pending').count()
    approved_count = Subject.objects.filter(status='approved').count()
    rejected_count = Subject.objects.filter(status='rejected').count()
    
    context = {
        'subjects': subjects,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'current_filter': current_filter,
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


# ===== EXAM LIST VIEW (FIXED) =====
@staff_member_required
def exam_list(request):
    """Admin view to list all exams with stat cards and batch actions."""
    exams = Exam.objects.select_related('course', 'subject', 'reviewed_by', 'teacher').all().order_by('-created_at')
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


# ===== CERTIFICATE LIST VIEW (FIXED) =====
@staff_member_required
def certificate_list(request):
    """Admin view to list all certificates with stat cards and batch actions."""
    certificates = Certificate.objects.select_related('user', 'lesson').all().order_by('-issued_date')
    total_count = certificates.count()
    by_lesson_count = certificates.exclude(lesson=None).count()
    unique_users_count = certificates.values('user').distinct().count()
    context = {
        'certificates': certificates,
        'total_count': total_count,
        'by_lesson_count': by_lesson_count,
        'unique_users_count': unique_users_count,
    }
    return render(request, 'dashboard/certificate_list.html', context)


# ===== BATCH CERTIFICATE ACTION =====
@staff_member_required
def batch_certificate_action(request):
    if request.method != 'POST':
        return redirect('certificate_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No certificates selected.")
        return redirect('certificate_list')
    if action == 'delete_selected_certificates':
        count = Certificate.objects.filter(id__in=selected_ids).count()
        Certificate.objects.filter(id__in=selected_ids).delete()
        messages.success(request, f"{count} certificate(s) deleted.")
    else:
        messages.error(request, "Invalid action.")
    return redirect('certificate_list')


# ===== COURSE LIST VIEW =====
@staff_member_required
def course_list(request):
    """Admin view to list all courses with stat cards and batch actions."""
    courses = Course.objects.all().order_by('code')
    total_count = courses.count()
    with_lessons_count = courses.filter(lessons__isnull=False).distinct().count()
    without_lessons_count = total_count - with_lessons_count
    for course in courses:
        course.lesson_count = Lesson.objects.filter(course=course).count()
    context = {
        'courses': courses,
        'total_count': total_count,
        'with_lessons_count': with_lessons_count,
        'without_lessons_count': without_lessons_count,
    }
    return render(request, 'dashboard/course_list.html', context)


# ===== BATCH COURSE ACTION =====
@staff_member_required
def batch_course_action(request):
    if request.method != 'POST':
        return redirect('course_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No courses selected.")
        return redirect('course_list')
    if action == 'delete_selected_courses':
        count = Course.objects.filter(id__in=selected_ids).count()
        Course.objects.filter(id__in=selected_ids).delete()
        messages.success(request, f"{count} course(s) deleted.")
    else:
        messages.error(request, "Invalid action.")
    return redirect('course_list')


# ===== EXAM RESULT LIST VIEW =====
@staff_member_required
def examresult_list(request):
    """Admin view to list all exam results with stat cards and batch actions."""
    from courses.models import ExamResult
    results = ExamResult.objects.select_related('user', 'exam').all().order_by('-date_taken')
    total_count = results.count()
    passed_count = results.filter(passed=True).count()
    failed_count = results.filter(passed=False).count()
    avg_percentage = results.aggregate(avg=Avg('percentage'))['avg'] or 0
    context = {
        'results': results,
        'total_count': total_count,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'avg_percentage': avg_percentage,
    }
    return render(request, 'dashboard/examresult_list.html', context)


# ===== BATCH EXAM RESULT ACTION =====
@staff_member_required
def batch_examresult_action(request):
    from courses.models import ExamResult
    if request.method != 'POST':
        return redirect('examresult_list')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No exam results selected.")
        return redirect('examresult_list')
    if action == 'delete_selected_examresults':
        count = ExamResult.objects.filter(id__in=selected_ids).count()
        ExamResult.objects.filter(id__in=selected_ids).delete()
        messages.success(request, f"{count} exam result(s) deleted.")
    else:
        messages.error(request, "Invalid action.")
    return redirect('examresult_list')


# ===== LESSON LIST VIEW =====
@staff_member_required
def lesson_list(request):
    """Admin view to list all lessons with stat cards and batch actions."""
    lessons = Lesson.objects.select_related('teacher').all().order_by('-created_at')
    total_count = lessons.count()
    pending_count = lessons.filter(status='pending').count()
    approved_count = lessons.filter(status='approved').count()
    rejected_count = lessons.filter(status='rejected').count()
    context = {
        'lessons': lessons,
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'dashboard/lesson_list.html', context)


# ===== BATCH LESSON ACTION (UPDATED WITH HARDCODED REDIRECT) =====
@staff_member_required
def batch_lesson_action(request):
    if request.method != 'POST':
        return redirect('/lessons/')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    if not selected_ids:
        messages.warning(request, "No lessons selected.")
        return redirect('/lessons/')
    queryset = Lesson.objects.filter(id__in=selected_ids)
    if action == 'approve_lessons':
        count = 0
        for lesson in queryset:
            lesson.status = 'approved'
            lesson.reviewed_by = request.user
            lesson.reviewed_at = datetime.now()
            lesson.save()
            count += 1
            create_notification(
                user=lesson.teacher,
                notification_type='lesson_approved',
                title='✅ Lesson Approved!',
                message=f'Your lesson "{lesson.title}" has been approved and is now live on the platform.',
                link=f'/courses/lesson/{lesson.id}/'
            )
        messages.success(request, f"{count} lesson(s) approved.")
    elif action == 'reject_lessons':
        count = 0
        for lesson in queryset:
            lesson.status = 'rejected'
            lesson.reviewed_by = request.user
            lesson.reviewed_at = datetime.now()
            lesson.save()
            count += 1
            create_notification(
                user=lesson.teacher,
                notification_type='system',
                title='❌ Lesson Rejected',
                message=f'Your lesson "{lesson.title}" has been rejected. Please review and resubmit.'
            )
        messages.success(request, f"{count} lesson(s) rejected.")
    elif action == 'delete_selected_lessons':
        count = queryset.count()
        queryset.delete()
        messages.success(request, f"{count} lesson(s) deleted.")
    else:
        messages.error(request, "Invalid action.")
    return redirect('/lessons/')

# ===== ADMIN WITHDRAWAL MANAGEMENT =====

@staff_member_required
def admin_withdrawal_requests(request):
    """Admin view to list all withdrawal requests."""
    status_filter = request.GET.get('status', '')
    withdrawal_requests = WithdrawalRequest.objects.select_related('teacher').all()
    
    if status_filter:
        withdrawal_requests = withdrawal_requests.filter(status=status_filter)
    
    # Stats
    pending_count = WithdrawalRequest.objects.filter(status='pending').count()
    approved_count = WithdrawalRequest.objects.filter(status='approved').count()
    rejected_count = WithdrawalRequest.objects.filter(status='rejected').count()
    total_count = WithdrawalRequest.objects.count()
    
    context = {
        'requests': withdrawal_requests,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_count': total_count,
        'current_filter': status_filter,
    }
    return render(request, 'dashboard/admin/withdrawal_list.html', context)


@staff_member_required
def admin_withdrawal_detail(request, pk):
    """Admin view to see details of a specific withdrawal request."""
    withdrawal = get_object_or_404(WithdrawalRequest, id=pk, select_related='teacher')
    return render(request, 'dashboard/admin/withdrawal_detail.html', {'withdrawal': withdrawal})


@staff_member_required
def approve_withdrawal(request, pk):
    """Admin action to approve a withdrawal request."""
    withdrawal = get_object_or_404(WithdrawalRequest, id=pk)
    
    if withdrawal.status != 'pending':
        messages.error(request, "This withdrawal request has already been processed.")
        return redirect('admin_withdrawal_detail', pk=pk)
    
    try:
        # Update wallet
        wallet = TeacherWallet.objects.get(teacher=withdrawal.teacher)
        
        # Deduct from available balance
        wallet.available_balance -= withdrawal.amount
        wallet.total_withdrawn += withdrawal.amount
        wallet.save()
        
        # Update withdrawal request
        withdrawal.status = 'approved'
        withdrawal.processed_at = datetime.now()
        withdrawal.save()
        
        # Find and update the associated earnings cycle
        cycle = EarningsCycle.objects.filter(
            teacher=withdrawal.teacher,
            status='claimed',
            amount=withdrawal.amount
        ).first()
        if cycle:
            cycle.status = 'paid'
            cycle.completed_at = datetime.now()
            cycle.save()
        
        # Send notification to teacher
        create_notification(
            user=withdrawal.teacher,
            notification_type='system',
            title='✅ Withdrawal Approved!',
            message=f'Your withdrawal request of {withdrawal.amount} FCFA has been approved and processed.',
            link='/dashboard/'
        )
        
        messages.success(request, f"Withdrawal of {withdrawal.amount} FCFA for {withdrawal.teacher.username} has been approved.")
        
    except Exception as e:
        messages.error(request, f"Error processing withdrawal: {str(e)}")
    
    return redirect('admin_withdrawal_detail', pk=pk)


@staff_member_required
def reject_withdrawal(request, pk):
    """Admin action to reject a withdrawal request."""
    withdrawal = get_object_or_404(WithdrawalRequest, id=pk)
    
    if withdrawal.status != 'pending':
        messages.error(request, "This withdrawal request has already been processed.")
        return redirect('admin_withdrawal_detail', pk=pk)
    
    if request.method == 'POST':
        admin_note = request.POST.get('admin_note', '').strip()
        
        if not admin_note:
            messages.error(request, "Please provide a reason for rejection.")
            return redirect('admin_withdrawal_detail', pk=pk)
        
        # Update withdrawal request
        withdrawal.status = 'rejected'
        withdrawal.admin_note = admin_note
        withdrawal.processed_at = datetime.now()
        withdrawal.save()
        
        # Find and update the associated earnings cycle (return to eligible)
        cycle = EarningsCycle.objects.filter(
            teacher=withdrawal.teacher,
            status='claimed',
            amount=withdrawal.amount
        ).first()
        if cycle:
            cycle.status = 'eligible'
            cycle.save()
        
        # Send notification to teacher
        create_notification(
            user=withdrawal.teacher,
            notification_type='system',
            title='❌ Withdrawal Rejected',
            message=f'Your withdrawal request of {withdrawal.amount} FCFA has been rejected. Reason: {admin_note}',
            link='/dashboard/'
        )
        
        messages.success(request, f"Withdrawal request for {withdrawal.teacher.username} has been rejected.")
        return redirect('admin_withdrawal_requests')
    
    # GET request - show rejection form
    return render(request, 'dashboard/admin/withdrawal_reject.html', {'withdrawal': withdrawal})