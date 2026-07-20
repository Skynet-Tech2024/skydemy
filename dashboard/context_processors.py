from users.models import UserProfile
from courses.models import Lesson, Exam, Certificate

def admin_stats(request):
    """Inject statistics into admin dashboard template."""
    print(f"CONTEXT PROCESSOR: admin_stats called, path={request.path}")
    
    student_count = UserProfile.objects.filter(role='learner').count()
    teacher_count = UserProfile.objects.filter(role='teacher').count()
    course_count = Lesson.objects.filter(status='approved').count()  # Only approved lessons
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()
    
    print(f"CONTEXT PROCESSOR: student={student_count}, teacher={teacher_count}, courses={course_count}, exams={exam_count}, certs={certificate_count}")
    
    return {
        'student_count': student_count,
        'teacher_count': teacher_count,
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
    }