from users.models import UserProfile
from courses.models import Lesson, Exam, Certificate
from django.urls import reverse
from django.core.exceptions import NoReverseMatch

def admin_stats(request):
    """Admin dashboard statistics and URLs."""

    # Counts
    learners = UserProfile.objects.filter(role='learner').count()
    teachers = UserProfile.objects.filter(role='teacher').count()
    course_count = Lesson.objects.count()
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()

    # Try to get UserProfile admin URLs dynamically
    userprofile_changelist_url = None
    userprofile_add_url = None
    try:
        # Construct URL using standard naming convention
        userprofile_changelist_url = reverse('admin:users_userprofile_changelist')
        userprofile_add_url = reverse('admin:users_userprofile_add')
    except NoReverseMatch:
        # If registration is missing, these will remain None
        pass

    return {
        'student_count': learners,
        'teacher_count': teachers,
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
        'userprofile_changelist_url': userprofile_changelist_url,
        'userprofile_add_url': userprofile_add_url,
    }