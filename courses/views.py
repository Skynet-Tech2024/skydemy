from users.utils import create_notification
from users.models import Wishlist
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from .forms import LessonForm, ExamForm
from .models import Subject, Lesson, Progress, Exam, ExamResult, Certificate

@login_required
def upload_lesson(request):
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can upload lessons.')
        return redirect('home')
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.teacher = request.user
            lesson.status = 'pending'  # Requires admin approval
            
            # Validation: subject for primary/secondary, course for university
            if lesson.level in ['primary', 'secondary'] and not lesson.subject:
                messages.error(request, 'Please select a subject for primary/secondary level.')
                return render(request, 'courses/upload_lesson.html', {'form': form})
            if lesson.level == 'university' and not lesson.course:
                messages.error(request, 'Please select a course for university level.')
                return render(request, 'courses/upload_lesson.html', {'form': form})
            
            lesson.save()
            
            # ----- Notification: New Lesson Uploaded (to followers) -----
            # Notify all followers of this teacher
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
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add subjects.')
        return redirect('home')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        level = request.POST.get('level')
        description = request.POST.get('description', '')
        
        if name and level:
            # Check if subject already exists
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
    lesson = Lesson.objects.get(id=lesson_id)
    exam = Exam.objects.filter(lesson=lesson, status='approved').first()  # Only show approved exams
    
    # Increment view counter
    lesson.views += 1
    lesson.save()
    
    # Track progress if user is authenticated and is a learner
    if request.user.is_authenticated and request.user.profile.role == 'learner':
        progress, created = Progress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={'progress_percentage': 10, 'total_pages': 1}
        )
        if not created and progress.progress_percentage < 100:
            # Increase progress gradually (simulate reading)
            progress.progress_percentage = min(100, progress.progress_percentage + 10)
            if progress.progress_percentage == 100:
                progress.completed = True
                # Update learner's completed lessons count and rating
                profile = request.user.profile
                profile.total_lessons_completed += 1
                profile.rating = profile.total_lessons_completed * 10  # 10 points per lesson
                profile.save()
            progress.save()
    
    return render(request, 'courses/view_lesson.html', {'lesson': lesson, 'exam': exam})

def lesson_list(request):
    # Only show approved lessons to learners and teachers
    lessons = Lesson.objects.filter(status='approved').order_by('-created_at')
    
    # Precompute follow and wishlist status for authenticated learners
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
def add_exam(request, lesson_id):
    lesson = Lesson.objects.get(id=lesson_id)
    
    # Only teachers can add exams
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add exams.')
        return redirect('home')
    
    # Check if exam already exists for this lesson
    existing_exam = Exam.objects.filter(lesson=lesson).first()
    if existing_exam:
        messages.info(request, f'An exam already exists for "{lesson.title}".')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.lesson = lesson
            exam.status = 'pending'  # Requires admin approval
            exam.save()
            messages.success(request, f'Exam "{exam.title}" created successfully and is pending admin review!')
            return redirect('view_lesson', lesson_id=lesson.id)
    else:
        form = ExamForm()
    
    return render(request, 'courses/add_exam.html', {'form': form, 'lesson': lesson})

@login_required
def take_exam(request, lesson_id):
    lesson = Lesson.objects.get(id=lesson_id)
    exam = Exam.objects.filter(lesson=lesson, status='approved').first()  # Only approved exams can be taken
    
    if not exam:
        messages.error(request, 'No approved exam available for this lesson.')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    # Check if user already took this exam
    existing_result = ExamResult.objects.filter(user=request.user, exam=exam).first()
    if existing_result:
        messages.info(request, f'You already took this exam. Score: {existing_result.percentage}%')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    if request.method == 'POST':
        # Process the exam answers
        questions = exam.questions
        score = 0
        total = len(questions)
        
        for i, q in enumerate(questions):
            user_answer = request.POST.get(f'question_{i}')
            if user_answer and user_answer == q.get('correct'):
                score += 1
        
        percentage = int((score / total) * 100) if total > 0 else 0
        passed = percentage >= exam.passing_score
        
        # Save the result
        result = ExamResult.objects.create(
            user=request.user,
            exam=exam,
            score=score,
            percentage=percentage,
            passed=passed
        )
        
        # ----- Notification: Exam Result -----
        if passed:
            create_notification(
                user=request.user,
                notification_type='exam_result',
                title='🎉 Exam Passed!',
                message=f'You passed "{exam.title}" with {percentage}%. Well done!',
                link=f'/courses/lesson/{lesson.id}/'
            )
        else:
            create_notification(
                user=request.user,
                notification_type='exam_result',
                title='📝 Exam Result',
                message=f'You scored {percentage}% on "{exam.title}". You need {exam.passing_score}% to pass. Keep trying!',
                link=f'/courses/lesson/{lesson.id}/'
            )
        
        # If passed, generate certificate
        if passed:
            certificate = Certificate.objects.create(
                user=request.user,
                lesson=lesson,
                exam=exam,
                score=percentage
            )
            
            # ----- Notification: Certificate Earned -----
            create_notification(
                user=request.user,
                notification_type='certificate_earned',
                title='🏆 Certificate Earned!',
                message=f'You earned a certificate for passing "{exam.title}" with {percentage}%. Certificate #: {certificate.certificate_number}',
                link=f'/dashboard/'
            )
            
            # Send email to admin
            subject = f'New Certificate Generated - {request.user.username}'
            message = f'''
            A new certificate has been generated:
            
            User: {request.user.username} ({request.user.email})
            Lesson: {lesson.title}
            Exam: {exam.title}
            Score: {percentage}%
            Certificate Number: {certificate.certificate_number}
            Date: {certificate.issued_date}
            
            Please review and verify the certificate.
            '''
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but continue
                pass
            
            messages.success(request, f'🎉 You passed! Score: {percentage}%. Certificate generated and admin notified!')
        else:
            messages.info(request, f'Score: {percentage}%. You need {exam.passing_score}% to pass. Try again!')
        
        return redirect('view_lesson', lesson_id=lesson.id)
    
    return render(request, 'courses/take_exam.html', {'exam': exam, 'lesson': lesson})