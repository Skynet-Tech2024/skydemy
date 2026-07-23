from users.models import UserProfile
from courses.models import Lesson, Exam, Certificate
from django.contrib.admin import site
from django.urls import reverse

def admin_stats(request):
    """Admin dashboard statistics and URLs."""

    # Counts
    total = UserProfile.objects.count()
    learners = UserProfile.objects.filter(role='learner').count()
    teachers = UserProfile.objects.filter(role='teacher').count()
    verified = UserProfile.objects.filter(verification_status='verified').count()
    approved = UserProfile.objects.filter(verification_status='approved').count()
    pending = UserProfile.objects.filter(verification_status='pending').count()
    premium = UserProfile.objects.filter(is_premium=True).count()

    course_count = Lesson.objects.count()
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()

    # Get admin URLs for UserProfile
    # The admin site may already have the model registered
    try:
        userprofile_model_admin = site._registry.get(UserProfile)
        if userprofile_model_admin:
            app_label = UserProfile._meta.app_label
            model_name = UserProfile._meta.model_name
            userprofile_changelist_url = reverse(f'admin:{app_label}_{model_name}_changelist')
            userprofile_add_url = reverse(f'admin:{app_label}_{model_name}_add')
        else:
            userprofile_changelist_url = None
            userprofile_add_url = None
    except Exception:
        userprofile_changelist_url = None
        userprofile_add_url = None

    return {
        'student_count': learners,
        'teacher_count': teachers,
        'verified_count': verified,
        'approved_count': approved,
        'pending_count': pending,
        'premium_count': premium,
        'total_count': total,
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
        'userprofile_changelist_url': userprofile_changelist_url,
        'userprofile_add_url': userprofile_add_url,
    }