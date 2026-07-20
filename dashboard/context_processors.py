from users.models import UserProfile
from courses.models import Lesson, Exam, Certificate

def admin_stats(request):
    """Inject statistics into admin dashboard template."""
    print(f"CONTEXT PROCESSOR: admin_stats called, path={request.path}")
    
    student_count = UserProfile.objects.filter(role='learner').count()
    teacher_count = UserProfile.objects.filter(role='teacher').count()
    verified_count = UserProfile.objects.filter(verification_status='verified').count()
    pending_count = UserProfile.objects.filter(verification_status='pending').count()
    premium_count = UserProfile.objects.filter(is_premium=True).count()
    
    course_count = Lesson.objects.filter(status='approved').count()
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()
    
    return {
        'student_count': student_count,
        'teacher_count': teacher_count,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'premium_count': premium_count,
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
    }