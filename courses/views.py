import json
from users.utils import create_notification
from users.models import Wishlist
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.http import JsonResponse
from .forms import LessonForm, ExamForm
from .models import Subject, Lesson, Progress, Exam, ExamResult, Certificate

# ====== Core Lesson Views ======

def lesson_list(request):
    """Display all approved lessons (public)."""
    lessons = Lesson.objects.filter(status='approved').order_by('-created_at')
    
    if request.user.is_authenticated and request.user.profile.role == 'learner':
        following_ids = request.user.following.values_list('following_id', flat=True)
        wishlisted_ids = Wishlist.objects.filter(user=request.user).values_list('lesson_id', flat=True)
        for lesson in lessons:
            lesson.is_following = lesson.teacher.id in following_ids
            lesson.is_wishlisted = lesson.id in wishlisted_ids
    else:
        for lesson in lessons:
            lesson.is_following = False
            lesson.is_wishlisted = False
    
    return render(request, 'courses/lesson_list.html', {'lessons': lessons})

@login_required
def upload_lesson(request):
    """Teachers upload a new lesson."""
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can upload lessons.')
        return redirect('home')
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.teacher = request.user
            lesson.status = 'pending'
            
            if lesson.level in ['primary', 'secondary'] and not lesson.subject:
                messages.error(request, 'Please select a subject for primary/secondary level.')
                return render(request, 'courses/upload_lesson.html', {'form': form})
            if lesson.level == 'university' and not lesson.course:
                messages.error(request, 'Please select a course for university level.')
                return render(request, 'courses/upload_lesson.html', {'form': form})
            
            lesson.save()
            
            # Notify followers
            followers = request.user.followers.all()
            for follow in followers:
                create_notification(
                    user=follow.follower,
                    notification_type='system',
                    title='📚 New Lesson from Teacher You Follow!',
                    message=f'Your followed teacher "{request.user.username}" has uploaded a new lesson: "{lesson.title}".',
                    link=f'/courses/lesson/{lesson.id}/'
                )
            
            messages.success(request, 'Lesson uploaded successfully and is pending admin review!')
            return redirect('dashboard')
    else:
        form = LessonForm()
    
    return render(request, 'courses/upload_lesson.html', {'form': form})

@login_required
def add_subject(request):
    """Teachers add a new subject."""
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add subjects.')
        return redirect('home')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        level = request.POST.get('level')
        description = request.POST.get('description', '')
        
        if name and level:
            existing = Subject.objects.filter(name__iexact=name, level=level).first()
            if existing:
                messages.info(request, f'Subject "{name}" already exists for this level.')
            else:
                Subject.objects.create(name=name, level=level, description=description)
                messages.success(request, f'Subject "{name}" created successfully!')
            return redirect('upload_lesson')
    
    return render(request, 'courses/add_subject.html')

@xframe_options_exempt
def view_lesson(request, lesson_id):
    """View a single lesson and its exam."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    exam = Exam.objects.filter(lesson=lesson, status='approved').first()
    
    lesson.views += 1
    lesson.save()
    
    if request.user.is_authenticated and request.user.profile.role == 'learner':
        progress, created = Progress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={'progress_percentage': 10, 'total_pages': 1}
        )
        if not created and progress.progress_percentage < 100:
            progress.progress_percentage = min(100, progress.progress_percentage + 10)
            if progress.progress_percentage == 100:
                progress.completed = True
                profile = request.user.profile
                profile.total_lessons_completed += 1
                profile.rating = profile.total_lessons_completed * 10
                profile.save()
            progress.save()
    
    return render(request, 'courses/view_lesson.html', {'lesson': lesson, 'exam': exam})

@login_required
def add_exam(request, lesson_id):
    """Add an exam to a specific lesson (teacher only)."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add exams.')
        return redirect('home')
    
    if Exam.objects.filter(lesson=lesson).exists():
        messages.info(request, f'An exam already exists for "{lesson.title}".')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.lesson = lesson
            exam.status = 'pending'
            exam.save()
            messages.success(request, f'Exam "{exam.title}" created and pending admin review!')
            return redirect('view_lesson', lesson_id=lesson.id)
    else:
        form = ExamForm()
    
    return render(request, 'courses/add_exam.html', {'form': form, 'lesson': lesson})

@login_required
def take_exam(request, lesson_id):
    """Learner takes an exam."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    exam = Exam.objects.filter(lesson=lesson, status='approved').first()
    
    if not exam:
        messages.error(request, 'No approved exam available for this lesson.')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    existing_result = ExamResult.objects.filter(user=request.user, exam=exam).first()
    if existing_result:
        messages.info(request, f'You already took this exam. Score: {existing_result.percentage}%')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    if request.method == 'POST':
        questions = exam.questions
        score = 0
        total = len(questions)
        
        for i, q in enumerate(questions):
            user_answer = request.POST.get(f'question_{i}')
            if user_answer and user_answer == q.get('correct'):
                score += 1
        
        percentage = int((score / total) * 100) if total > 0 else 0
        passed = percentage >= exam.passing_score
        
        result = ExamResult.objects.create(
            user=request.user,
            exam=exam,
            score=score,
            percentage=percentage,
            passed=passed
        )
        
        if passed:
            create_notification(
                user=request.user,
                notification_type='exam_result',
                title='🎉 Exam Passed!',
                message=f'You passed "{exam.title}" with {percentage}%. Well done!',
                link=f'/courses/lesson/{lesson.id}/'
            )
            # Generate certificate
            certificate = Certificate.objects.create(
                user=request.user,
                lesson=lesson,
                exam=exam,
                score=percentage
            )
            create_notification(
                user=request.user,
                notification_type='certificate_earned',
                title='🏆 Certificate Earned!',
                message=f'You earned a certificate for passing "{exam.title}" with {percentage}%. Certificate #: {certificate.certificate_number}',
                link=f'/dashboard/'
            )
            # Email admin
            send_mail(
                f'New Certificate Generated - {request.user.username}',
                f'User: {request.user.username} ({request.user.email})\nLesson: {lesson.title}\nExam: {exam.title}\nScore: {percentage}%\nCertificate: {certificate.certificate_number}',
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True,
            )
            messages.success(request, f'🎉 You passed! Score: {percentage}%. Certificate generated!')
        else:
            create_notification(
                user=request.user,
                notification_type='exam_result',
                title='📝 Exam Result',
                message=f'You scored {percentage}% on "{exam.title}". You need {exam.passing_score}% to pass. Keep trying!',
                link=f'/courses/lesson/{lesson.id}/'
            )
            messages.info(request, f'Score: {percentage}%. You need {exam.passing_score}% to pass.')
        
        return redirect('view_lesson', lesson_id=lesson.id)
    
    return render(request, 'courses/take_exam.html', {'exam': exam, 'lesson': lesson})

# ========== EXAM MANAGEMENT FOR TEACHERS ==========

@login_required
def add_fslc_papers(request):
    if request.user.profile.level != 'primary':
        messages.error(request, "You are not authorized to add FSLC papers.")
        return redirect('lesson_list')
    
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        return redirect('add_exam', lesson_id=lesson_id)
    else:
        lessons = Lesson.objects.filter(teacher=request.user)
        return render(request, 'courses/select_lesson_for_exam.html', {'lessons': lessons, 'exam_type': 'FSLC'})

@login_required
def add_mock_papers_primary(request):
    if request.user.profile.level != 'primary':
        messages.error(request, "You are not authorized to add mock papers.")
        return redirect('lesson_list')
    
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        return redirect('add_exam', lesson_id=lesson_id)
    else:
        lessons = Lesson.objects.filter(teacher=request.user)
        return render(request, 'courses/select_lesson_for_exam.html', {'lessons': lessons, 'exam_type': 'Mock (Primary)'})

@login_required
def select_mock_exam_level(request):
    if request.user.profile.level != 'secondary':
        messages.error(request, "You are not authorized.")
        return redirect('lesson_list')
    return render(request, 'courses/select_mock_level.html')

@login_required
def select_gce_level(request):
    if request.user.profile.level != 'secondary':
        messages.error(request, "You are not authorized.")
        return redirect('lesson_list')
    return render(request, 'courses/select_gce_level.html')

@login_required
def add_mock_exam(request, level):
    if request.user.profile.level != 'secondary':
        messages.error(request, "You are not authorized.")
        return redirect('lesson_list')
    
    lessons = Lesson.objects.filter(teacher=request.user, level=level)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        questions_json = request.POST.get('questions')
        lesson_id = request.POST.get('lesson')
        
        try:
            questions = json.loads(questions_json)
            if not isinstance(questions, list) or not questions:
                messages.error(request, "Invalid questions format. Must be a non-empty JSON array.")
                return render(request, 'courses/add_mock_exam.html', {'level': level, 'lessons': lessons})
            
            exam = Exam(
                title=title,
                questions=questions_json,
                teacher=request.user,
                level=level,
                exam_type='mock',
                lesson_id=lesson_id if lesson_id else None
            )
            exam.save()
            messages.success(request, f"Mock exam '{title}' created successfully!")
            return redirect('lesson_list')
        except json.JSONDecodeError:
            messages.error(request, "Invalid JSON format. Please check your syntax.")
        except Exception as e:
            messages.error(request, f"Error saving exam: {e}")
    
    return render(request, 'courses/add_mock_exam.html', {'level': level, 'lessons': lessons})

@login_required
def add_gce_past_questions(request, level):
    if request.user.profile.level != 'secondary':
        messages.error(request, "You are not authorized.")
        return redirect('lesson_list')
    
    subjects = Subject.objects.all()
    
    if request.method == 'POST':
        title = request.POST.get('title')
        year = request.POST.get('year')
        questions_json = request.POST.get('questions')
        subject_id = request.POST.get('subject')
        
        try:
            questions = json.loads(questions_json)
            if not isinstance(questions, list) or not questions:
                messages.error(request, "Invalid questions format. Must be a non-empty JSON array.")
                return render(request, 'courses/add_gce_past_questions.html', {'level': level, 'subjects': subjects})
            
            exam = Exam(
                title=title,
                questions=questions_json,
                teacher=request.user,
                level=level,
                exam_type='gce',
                subject_id=subject_id if subject_id else None,
                year=year
            )
            exam.save()
            messages.success(request, f"GCE past questions '{title}' created successfully!")
            return redirect('lesson_list')
        except json.JSONDecodeError:
            messages.error(request, "Invalid JSON format. Please check your syntax.")
        except Exception as e:
            messages.error(request, f"Error saving exam: {e}")
    
    return render(request, 'courses/add_gce_past_questions.html', {'level': level, 'subjects': subjects})