import sys
from users.models import UserProfile
from courses.models import Course, Exam, Certificate

def admin_stats(request):
    print(f"CONTEXT PROCESSOR: admin_stats called, path={request.path}", file=sys.stderr)
    sys.stderr.flush()
    
    student_count = UserProfile.objects.filter(role='learner').count()
    teacher_count = UserProfile.objects.filter(role='teacher').count()
    course_count = Course.objects.count()
    exam_count = Exam.objects.count()
    certificate_count = Certificate.objects.count()
    
    print(f"CONTEXT PROCESSOR: student={student_count}, teacher={teacher_count}", file=sys.stderr)
    sys.stderr.flush()
    
    return {
        'student_count': student_count,
        'teacher_count': teacher_count,
        'course_count': course_count,
        'exam_count': exam_count,
        'certificate_count': certificate_count,
    }