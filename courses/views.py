import os
import json
import re
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from users.utils import create_notification
from users.models import Wishlist
from users.decorators import basic_access, lesson_access, upload_access, video_lesson_access, profile_access
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from .forms import LessonForm, ExamForm
from .models import Subject, Lesson, Progress, Exam, ExamResult, Certificate

# ====== Core Lesson Views ======

@basic_access
def lesson_list(request):
    """Display lessons – learners see only their level, teachers see all."""
    lessons = Lesson.objects.filter(status='approved').order_by('-created_at')
    
    if request.user.is_authenticated and request.user.profile.role == 'learner':
        # Learner: only show lessons of their level
        lessons = lessons.filter(level=request.user.profile.level)
        following_ids = request.user.following.values_list('following_id', flat=True)
        wishlisted_ids = Wishlist.objects.filter(user=request.user).values_list('lesson_id', flat=True)
        for lesson in lessons:
            lesson.is_following = lesson.teacher.id in following_ids
            lesson.is_wishlisted = lesson.id in wishlisted_ids
    else:
        # Teacher/admin: show all lessons, no following/wishlist flags
        for lesson in lessons:
            lesson.is_following = False
            lesson.is_wishlisted = False
    
    return render(request, 'courses/lesson_list.html', {'lessons': lessons})

@upload_access
def upload_lesson(request):
    """Teachers upload a new lesson – level is forced to teacher's level."""
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can upload lessons.')
        return redirect('home')

    teacher_level = request.user.profile.level

    # If the teacher has no level set, redirect them to profile
    if not teacher_level:
        messages.error(request, 'Please set your education level in your profile before uploading a lesson.')
        return redirect('profile')

    if request.method == 'POST':
        # Remove level from POST data – we'll set it manually
        post_data = request.POST.copy()
        post_data.pop('level', None)
        form = LessonForm(post_data, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.teacher = request.user
            lesson.status = 'pending'
            # Force lesson level to match teacher's level
            lesson.level = teacher_level

            if lesson.level in ['primary', 'secondary'] and not lesson.subject:
                messages.error(request, 'Please select a subject for primary/secondary level.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
            if lesson.level == 'university' and not lesson.course:
                messages.error(request, 'Please select a course for university level.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})

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
            # Form invalid – re‑render with teacher_level
            return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
    else:
        # Pre-populate level with teacher's level and make it disabled
        form = LessonForm(initial={'level': teacher_level})
        form.fields['level'].disabled = True
        form.fields['level'].widget.attrs['readonly'] = True

    return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})

@upload_access
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
@lesson_access
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
    
    # Check if user can view video (verified only)
    can_view_video = False
    if request.user.is_authenticated and request.user.profile.verification_status == 'verified':
        can_view_video = True
    elif request.user.is_authenticated and request.user.is_superuser:
        can_view_video = True
    
    return render(request, 'courses/view_lesson.html', {
        'lesson': lesson,
        'exam': exam,
        'can_view_video': can_view_video
    })


def parse_exam_file(file):
    """Parse exam file (PDF or DOCX) and return list of questions in JSON format."""
    content = ""
    file_name = file.name.lower()
    
    if file_name.endswith('.pdf'):
        try:
            import pdfplumber
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n"
        except ImportError:
            raise ImportError("pdfplumber is not installed. Run: pip install pdfplumber")
    elif file_name.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(file)
            for para in doc.paragraphs:
                if para.text:
                    content += para.text + "\n"
        except ImportError:
            raise ImportError("python-docx is not installed. Run: pip install python-docx")
    else:
        raise ValueError("Unsupported file format. Use PDF or DOCX.")
    
    if not content.strip():
        raise ValueError("No text could be extracted from the file.")
    
    # Parse content into questions
    questions = []
    lines = content.split('\n')
    current_question = None
    current_options = []
    current_correct = None
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_question and current_options:
                q = {
                    'question': current_question,
                    'options': current_options,
                    'correct': current_correct or (current_options[0] if current_options else "")
                }
                questions.append(q)
                current_question = None
                current_options = []
                current_correct = None
            continue
        
        question_match = re.match(r'^(\d+)[\.\)]\s*(.*)', line)
        if question_match:
            if current_question and current_options:
                q = {
                    'question': current_question,
                    'options': current_options,
                    'correct': current_correct or (current_options[0] if current_options else "")
                }
                questions.append(q)
            current_question = question_match.group(2).strip()
            current_options = []
            current_correct = None
            continue
        
        option_match = re.match(r'^([A-D])[\.\)]\s*(.*)', line, re.IGNORECASE)
        if option_match and current_question is not None:
            option_text = option_match.group(2).strip()
            current_options.append(option_text)
            if '*' in option_text or '(correct)' in option_text.lower():
                current_correct = option_text
            continue
        
        answer_match = re.match(r'^Answers?\s*[:;]\s*(.*)', line, re.IGNORECASE)
        if answer_match and questions:
            answer_key = answer_match.group(1).strip()
            parts = re.split(r'[,\s]+', answer_key)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                num_letter = re.match(r'^(\d+)\s*([A-D])', part, re.IGNORECASE)
                if num_letter:
                    q_num = int(num_letter.group(1))
                    ans_letter = num_letter.group(2).upper()
                    if q_num <= len(questions):
                        opt_idx = ord(ans_letter) - ord('A')
                        if opt_idx < len(questions[q_num-1]['options']):
                            questions[q_num-1]['correct'] = questions[q_num-1]['options'][opt_idx]
            continue
        
        if current_question is not None:
            if current_options:
                current_options[-1] += " " + line
            else:
                current_question += " " + line
    
    if current_question and current_options:
        q = {
            'question': current_question,
            'options': current_options,
            'correct': current_correct or (current_options[0] if current_options else "")
        }
        questions.append(q)
    
    if not questions:
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            parts = re.split(r'[A-D]\s*[:.]\s*', line, flags=re.IGNORECASE)
            if len(parts) >= 2:
                question_text = parts[0].strip()
                options = [p.strip() for p in parts[1:] if p.strip()]
                if question_text and options:
                    questions.append({
                        'question': question_text,
                        'options': options,
                        'correct': options[0]
                    })
    
    return questions


@upload_access
def add_exam(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add exams.')
        return redirect('home')
    
    if Exam.objects.filter(lesson=lesson).exists():
        messages.info(request, f'An exam already exists for "{lesson.title}".')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    if request.method == 'POST':
        exam_file = request.FILES.get('exam_file')
        json_questions = request.POST.get('questions')
        title = request.POST.get('title')
        passing_score = request.POST.get('passing_score', 50)
        
        questions = None
        if exam_file:
            try:
                questions = parse_exam_file(exam_file)
                if not questions:
                    messages.error(request, 'No questions could be parsed from the file. Please check the format.')
                    return render(request, 'courses/add_exam.html', {'lesson': lesson})
            except Exception as e:
                messages.error(request, f'Error parsing file: {e}')
                return render(request, 'courses/add_exam.html', {'lesson': lesson})
        elif json_questions:
            try:
                questions = json.loads(json_questions)
                if not isinstance(questions, list) or not questions:
                    messages.error(request, 'Invalid JSON format. Must be a non-empty array.')
                    return render(request, 'courses/add_exam.html', {'lesson': lesson})
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON format. Please check your syntax.')
                return render(request, 'courses/add_exam.html', {'lesson': lesson})
        else:
            messages.error(request, 'Please provide either a file or JSON questions.')
            return render(request, 'courses/add_exam.html', {'lesson': lesson})
        
        exam = Exam(
            lesson=lesson,
            title=title or f"Exam for {lesson.title}",
            passing_score=int(passing_score) if passing_score else 50,
            questions=questions,
            status='pending'
        )
        exam.save()
        messages.success(request, f'Exam "{exam.title}" created and pending admin review!')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    return render(request, 'courses/add_exam.html', {'lesson': lesson})


@lesson_access
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


# ====== CONVERT LESSON TO VIDEO ======

@upload_access
def convert_to_video(request, lesson_id):
    """
    Convert a lesson to an illustrative video.
    Verified users (teachers) can convert their lessons to videos.
    """
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Check if the current user is the teacher of this lesson or an admin
    if request.user != lesson.teacher and not request.user.is_superuser:
        messages.error(request, "You can only convert your own lessons.")
        return redirect('view_lesson', lesson_id=lesson.id)
    
    # Only verified users can convert to video
    if request.user.profile.verification_status != 'verified' and not request.user.is_superuser:
        messages.error(request, "Only verified teachers can convert lessons to video. Please contact admin.")
        return redirect('view_lesson', lesson_id=lesson.id)
    
    # Check if lesson already has a video
    if lesson.video_url or lesson.video_file:
        messages.warning(request, "This lesson already has a video.")
        return redirect('view_lesson', lesson_id=lesson.id)
    
    # --- VIDEO GENERATION LOGIC ---
    # Placeholder: In production, integrate with a video generation service
    # like HeyGen, Synthesia, or use a library like moviepy to create a video
    # from lesson content (text-to-speech + slides)
    
    # For now, we'll simulate the process:
    # 1. Extract content from lesson
    # 2. Generate a video using a service
    # 3. Store the video URL or file
    
    # Simulated video URL (replace with actual service call)
    video_url = "https://example.com/videos/generated/" + str(lesson.id) + ".mp4"
    video_url = None  # Keep as None until actual implementation
    
    if video_url:
        lesson.video_url = video_url
        lesson.save()
        messages.success(request, f'🎬 Video successfully generated for "{lesson.title}"!')
        
        # Notify the teacher
        create_notification(
            user=request.user,
            notification_type='system',
            title='🎬 Video Generated!',
            message=f'Your lesson "{lesson.title}" has been converted to an illustrative video.',
            link=f'/courses/lesson/{lesson.id}/'
        )
    else:
        messages.info(request, "Video conversion is being processed. You will be notified when it's ready.")
        # Here you can trigger a background task (Celery, Redis, etc.)
        # For now, just show a placeholder message
    
    return redirect('view_lesson', lesson_id=lesson.id)


# ========== EXAM MANAGEMENT FOR TEACHERS ==========

@upload_access
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

@upload_access
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

@upload_access
def select_mock_exam_level(request):
    if request.user.profile.level != 'secondary':
        messages.error(request, "You are not authorized.")
        return redirect('lesson_list')
    return render(request, 'courses/select_mock_level.html')

@upload_access
def select_gce_level(request):
    if request.user.profile.level != 'secondary':
        messages.error(request, "You are not authorized.")
        return redirect('lesson_list')
    return render(request, 'courses/select_gce_level.html')

@upload_access
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

@upload_access
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