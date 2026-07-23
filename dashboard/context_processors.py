from users.models import UserProfile
from courses.models import Lesson, Exam, Certificate  # Import the models

def admin_stats(request):
    """Admin dashboard statistics for user management and content counts."""

    # Get the current queryset from the changelist if available
    queryset = UserProfile.objects.all()

    # Check if we're on the userprofile changelist with filters
    if request.path == '/admin/users/userprofile/':
        # Get filters from GET parameters
        get_params = request.GET

        # Apply filters to the queryset if they exist
        if 'role__exact' in get_params and get_params['role__exact']:
            queryset = queryset.filter(role=get_params['role__exact'])
        if 'verification_status__exact' in get_params and get_params['verification_status__exact']:
            queryset = queryset.filter(verification_status=get_params['verification_status__exact'])
        if 'level__exact' in get_params and get_params['level__exact']:
            queryset = queryset.filter(level=get_params['level__exact'])
        if 'is_premium__exact' in get_params:
            val = get_params['is_premium__exact']
            if val == 'True':
                queryset = queryset.filter(is_premium=True)
            elif val == 'False':
                queryset = queryset.filter(is_premium=False)

    # Counts based on the filtered queryset (for user stats)
    total = queryset.count()
    learners = queryset.filter(role='learner').count()
    teachers = queryset.filter(role='teacher').count()
    verified = queryset.filter(verification_status='verified').count()
    approved = queryset.filter(verification_status='approved').count()
    pending = queryset.filter(verification_status='pending').count()
    premium = queryset.filter(is_premium=True).count()

    # ===== ADD COUNTS FOR OTHER MODELS =====
    course_count = Lesson.objects.count()         # Total lessons (linked to "Courses" card)
    exam_count = Exam.objects.count()             # Total exams
    certificate_count = Certificate.objects.count()  # Total certificates

    return {
        'student_count': learners,
        'teacher_count': teachers,
        'verified_count': verified,
        'approved_count': approved,
        'pending_count': pending,
        'premium_count': premium,
        'total_count': total,
        # New counts for the dashboard cards
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
    }