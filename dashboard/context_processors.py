from users.models import UserProfile
from courses.models import Lesson, Exam, Certificate
from django.urls import reverse, NoReverseMatch

def admin_stats(request):
    """Admin dashboard statistics and URLs."""

    # Counts
    student_count = UserProfile.objects.filter(role='learner').count()
    teacher_count = UserProfile.objects.filter(role='teacher').count()
    course_count = Lesson.objects.count()
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()

    # Get UserProfile admin URL
    userprofile_admin_url = None
    try:
        userprofile_admin_url = reverse('admin:users_userprofile_changelist')
    except NoReverseMatch:
        pass

    return {
        'student_count': student_count,
        'teacher_count': teacher_count,
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
        'userprofile_admin_url': userprofile_admin_url,
    }