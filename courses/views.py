import os
import json
import re
import tempfile
import urllib.parse
import logging
from datetime import datetime, timedelta

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse, HttpResponse, HttpResponseServerError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import get_template

# Users & notifications
from users.utils import create_notification
from users.models import SavedLesson as Wishlist
from users.decorators import lesson_access, upload_access

# Cloudinary
import cloudinary
import cloudinary.api
import cloudinary.uploader
import requests
from cloudinary.utils import cloudinary_url

# Forms and models
from .forms import LessonForm, ExamCreationForm, CertificateIssueForm, CourseCreationForm
from .models import Subject, Lesson, Exam, ExamResult, Certificate, Course, LessonProgress
from .utils import convert_uploaded_file_to_pdf

logger = logging.getLogger(__name__)


# ====== HELPER: Safe video URL ======
def get_video_url(lesson):
    """Return the URL of the whiteboard video if it exists, else None."""
    if hasattr(lesson, 'whiteboard_video') and lesson.whiteboard_video:
        if hasattr(lesson.whiteboard_video, 'url'):
            return lesson.whiteboard_video.url
        return lesson.whiteboard_video
    return None


@login_required
def convert_lesson_to_whiteboard(request, lesson_id):
    """
    Convert a lesson's PDF to a whiteboard video using Cloudinary's cloud processing.
    """
    lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)

    if not lesson.pdf_file:
        messages.error(request, "This lesson has no PDF to convert.")
        return redirect('courses:view_lesson', lesson_id=lesson.id)

    # Delete any existing video
    if lesson.whiteboard_video:
        lesson.whiteboard_video.delete(save=False)

    # Get the public ID (remove extension)
    public_id = lesson.pdf_file.name
    if '.' in public_id:
        public_id = public_id.rsplit('.', 1)[0]

    if not public_id:
        messages.error(request, "Could not determine public ID for PDF.")
        return redirect('courses:view_lesson', lesson_id=lesson.id)

    try:
        # --- 1. Request Cloudinary to generate a video from the PDF ---
        result = cloudinary.uploader.explicit(
            public_id,
            resource_type='image',
            type='upload',
            eager=[
                {
                    "format": "mp4",
                    "resource_type": "video",
                    "video_codec": "h264",
                    "audio_codec": "none"
                }
            ]
        )

        # --- 2. Get the generated video URL from the eager result ---
        eager = result.get('eager', [])
        if not eager:
            messages.error(request, "Cloudinary did not return a video URL. Please try again.")
            return redirect('courses:view_lesson', lesson_id=lesson.id)

        video_url = eager[0].get('secure_url')
        if not video_url:
            messages.error(request, "Could not extract video URL from Cloudinary response.")
            return redirect('courses:view_lesson', lesson_id=lesson.id)

        # --- 3. Download the video and save it to the lesson ---
        response = requests.get(video_url)
        if response.status_code != 200:
            messages.error(request, f"Failed to download video from Cloudinary (HTTP {response.status_code}).")
            return redirect('courses:view_lesson', lesson_id=lesson.id)

        # Save the video file
        lesson.whiteboard_video.save(
            f"whiteboard_{lesson.id}.mp4",
            ContentFile(response.content),
            save=True
        )

        messages.success(request, "✅ Whiteboard video created successfully using Cloudinary!")

    except Exception as e:
        logger.error(f"Cloudinary conversion failed: {str(e)}", exc_info=True)
        messages.error(request, f"Conversion failed: {str(e)}")

    return redirect('courses:view_lesson', lesson_id=lesson.id)


# ====== Core Lesson Views ======


@login_required
def lesson_list(request):
    """Display lessons – accessible to all authenticated users."""
    try:
        print("✅ lesson_list view called!")   # debug

        lessons_qs = Lesson.objects.filter(status='approved').order_by('-created_at')

        # ===== ROLE-BASED FILTERING =====
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'teacher':
                # Teachers see all approved lessons
                pass  # no additional filter
            elif request.user.profile.role == 'learner':
                # Learners: filter by their selected levels
                learner_levels = request.user.profile.levels.all()
                if learner_levels.exists():
                    level_codes = [level.code for level in learner_levels]
                    lessons_qs = lessons_qs.filter(level__in=level_codes)
                else:
                    # If learner has no levels assigned, show no lessons
                    lessons_qs = lessons_qs.none()

        # Search
        query = request.GET.get('q')
        if query:
            lessons_qs = lessons_qs.filter(
                Q(title__icontains=query) |
                Q(subject__name__icontains=query) |
                Q(teacher__username__icontains=query)
            )

        # Pagination
        paginator = Paginator(lessons_qs, 12)
        page_obj = paginator.get_page(request.GET.get('page'))

        # Attach following/wishlist info for learners
        if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'learner':
            following_ids = request.user.following.values_list('following_id', flat=True)
            wishlisted_ids = Wishlist.objects.filter(user=request.user).values_list('lesson_id', flat=True)
            for lesson in page_obj:
                # Safety: if teacher is None, treat as not following
                if lesson.teacher:
                    lesson.is_following = lesson.teacher.id in following_ids
                else:
                    lesson.is_following = False
                lesson.is_wishlisted = lesson.id in wishlisted_ids
        else:
            for lesson in page_obj:
                lesson.is_following = False
                lesson.is_wishlisted = False

        # Ensure each lesson has a 'whiteboard_video' attribute (even if None)
        for lesson in page_obj:
            if not hasattr(lesson, 'whiteboard_video'):
                lesson.whiteboard_video = None

        return render(request, 'courses/lesson_list.html', {
            'page_obj': page_obj,
            'query': query,
        })
    except Exception as e:
        logger.error(f"Lesson list error: {str(e)}", exc_info=True)
        if settings.DEBUG:
            return HttpResponseServerError(f"<h1>Error in lesson_list</h1><pre>{str(e)}</pre>")
        else:
            messages.error(request, "We're having trouble loading lessons. Please try again later.")
            return render(request, 'dashboard/base.html', {'content': '<p>Error loading lessons. Please refresh or try again later.</p>'})


@upload_access
def upload_lesson(request):
    """Teachers upload a new lesson – level is chosen from teacher's assigned levels."""
    print("🔥 upload_lesson called, method:", request.method)

    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can upload lessons.')
        return redirect('home')

    # Get teacher's assigned levels (many‑to‑many)
    teacher_levels = request.user.profile.levels.all()

    if not teacher_levels.exists():
        messages.error(request, 'Please set your education level(s) in your profile before uploading a lesson.')
        return redirect('profile')

    # Determine if course field should be shown (only if teacher has 'university' level)
    show_course = teacher_levels.filter(code='university').exists()

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, teacher_levels=teacher_levels)

        if form.is_valid():
            print("✅ Form is valid!")
            print(f"Lesson title: {form.cleaned_data.get('title')}")
            print(f"Selected level: {form.cleaned_data.get('level')}")
            print(f"PDF file: {request.FILES.get('pdf_file')}")

            lesson = form.save(commit=False)
            lesson.teacher = request.user

            # --- Handle new subject creation ---
            selected_subject_id = request.POST.get('subject')
            new_subject_name = request.POST.get('new_subject_name', '').strip()
            new_subject_code = request.POST.get('new_subject_code', '').strip()

            if selected_subject_id:
                try:
                    lesson.subject = Subject.objects.get(id=selected_subject_id)
                except Subject.DoesNotExist:
                    messages.error(request, 'Selected subject does not exist.')
                    return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})
            elif new_subject_name and new_subject_code:
                # Check if a subject with this code already exists (global uniqueness)
                if Subject.objects.filter(code__iexact=new_subject_code).exists():
                    messages.error(request, f'Subject code "{new_subject_code}" is already in use. Please choose a different code.')
                    return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})
                else:
                    level_code = form.cleaned_data.get('level')
                    # Create new subject (same name allowed if code differs)
                    subject = Subject.objects.create(
                        name=new_subject_name,
                        code=new_subject_code,
                        level=level_code,
                        proposed_by=request.user,
                        status='pending'
                    )
                    lesson.subject = subject
                    messages.success(request, f'New subject "{subject.name}" created with code "{subject.code}" and pending approval.')
            else:
                messages.error(request, 'Please select an existing subject or provide a name and code for a new subject.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})

            # --- Handle file conversion (Word to PDF) ---
            uploaded_file = request.FILES.get('pdf_file')
            if uploaded_file:
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                if ext in ['.doc', '.docx']:
                    try:
                        pdf_file_obj = convert_uploaded_file_to_pdf(uploaded_file)
                        lesson.pdf_file = pdf_file_obj
                        lesson.is_converted = True
                        lesson.original_file = uploaded_file
                    except Exception as e:
                        messages.error(request, f"Failed to convert Word document: {e}")
                        return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})
                else:
                    lesson.pdf_file = uploaded_file
                    lesson.is_converted = False

            # Validate subject/course based on level
            if lesson.level in ['primary', 'secondary'] and not lesson.subject:
                messages.error(request, 'Please select a subject or create a new one for primary/secondary level.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})
            if lesson.level == 'university' and not lesson.course:
                messages.error(request, 'Please select a course for university level.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})

            # ---- Determine action: draft or submit ----
            action = request.POST.get('action')
            if action == 'draft':
                lesson.status = 'draft'
                lesson.save()
                print(f"✅ Lesson saved! ID: {lesson.id}, Status: {lesson.status}")
                messages.success(request, '📝 Your lesson has been saved as a draft. You can continue editing later.')
            else:
                lesson.status = 'pending'
                lesson.save()
                print(f"✅ Lesson saved! ID: {lesson.id}, Status: {lesson.status}")
                messages.success(
                    request,
                    '🎉 Great Job! Your lesson has been submitted for review. '
                    'Our administrators will verify the content before making it available to learners. '
                    'Thank you for helping students learn with SKYDEMY!'
                )

                # Notify followers only when submitted (not draft)
                followers = request.user.followers.all()
                for follow in followers:
                    create_notification(
                        user=follow.follower,
                        notification_type='system',
                        title='📚 New Lesson from Teacher You Follow!',
                        message=f'Your followed teacher "{request.user.username}" has uploaded a new lesson: "{lesson.title}".',
                        link=f'/courses/lesson/{lesson.id}/'
                    )

            return redirect('courses:lesson_list')
        else:
            print("❌ Form is INVALID!")
            print(f"Form errors: {form.errors}")
            return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_levels': teacher_levels, 'show_course': show_course})
    else:
        form = LessonForm(teacher_levels=teacher_levels)

    template_name = 'courses/upload_lesson.html'
    print(f"Rendering template: {template_name}")
    try:
        template = get_template(template_name)
        print(f"Template loaded successfully from: {template.origin.name}")
    except Exception as e:
        print(f"Template load error: {e}")

    return render(request, template_name, {
        'form': form,
        'teacher_levels': teacher_levels,
        'show_course': show_course,
    })


@upload_access
def add_subject(request):
    """Teachers add a new subject with name, code, level, and optional cycle."""
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add subjects.')
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        level = request.POST.get('level')
        cycle = request.POST.get('cycle', '')

        # Validate required fields
        if not name:
            messages.error(request, 'Subject name is required.')
            return render(request, 'courses/add_subject.html')
        if not code:
            messages.error(request, 'Subject code is required.')
            return render(request, 'courses/add_subject.html')
        if not level:
            messages.error(request, 'Please select a level.')
            return render(request, 'courses/add_subject.html')

        # If secondary, cycle is required
        if level == 'secondary' and not cycle:
            messages.error(request, 'Please select a cycle for secondary level.')
            return render(request, 'courses/add_subject.html')

        # Check if the code is already used (global uniqueness)
        if Subject.objects.filter(code__iexact=code).exists():
            messages.error(request, f'Subject code "{code}" is already in use. Please choose a different code.')
            return render(request, 'courses/add_subject.html')

        # Create subject (duplicate name+level allowed if code differs)
        Subject.objects.create(
            name=name,
            code=code,
            level=level,
            cycle=cycle if level == 'secondary' else None,
            proposed_by=request.user,
            status='pending'
        )
        messages.success(request, f'Subject "{name}" (code: {code}) has been submitted for review!')
        return redirect('courses:upload_lesson')

    return render(request, 'courses/add_subject.html')


# ====== PDF READER WITH BASIC PROGRESS ======

@xframe_options_exempt
@login_required
def view_lesson(request, lesson_id):
    """View a lesson with a PDF reader."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    exam = None

    if request.user.is_authenticated:
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={
                'current_page': 1,
                'total_pages': 1,
                'progress_percentage': 0,
                'completed': False
            }
        )
    else:
        progress = None

    pdf_url = None
    if lesson.pdf_file:
        try:
            pdf_url = default_storage.url(lesson.pdf_file.name)
            print(f"DEBUG: PDF URL = {pdf_url}")
        except Exception as e:
            pdf_url = None
            messages.warning(request, f"Could not generate PDF URL: {str(e)}")

    total_pages = progress.total_pages if progress else 1
    current_page = progress.current_page if progress else 1

    context = {
        'lesson': lesson,
        'exam': exam,
        'pdf_url': pdf_url,
        'progress': progress,
        'total_pages': total_pages,
        'current_page': current_page,
    }

    print("📄 TEMPLATE: courses/lesson_reader.html")
    return render(request, 'courses/lesson_reader.html', context)


@login_required
def watch_whiteboard_video(request, lesson_id):
    """Display the whiteboard video using the lesson reader template."""
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if not lesson.whiteboard_video:
        messages.error(request, "This lesson does not have a whiteboard video yet.")
        return redirect('courses:view_lesson', lesson_id=lesson.id)

    context = {
        'lesson': lesson,
        'show_video': True,
        'pdf_url': None,
        'progress': None,
        'total_pages': 1,
        'current_page': 1,
    }
    return render(request, 'courses/lesson_reader.html', context)


@login_required
@csrf_exempt
def save_lesson_progress(request):
    """AJAX endpoint to save reading progress."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        lesson_id = data.get('lesson_id')
        current_page = data.get('current_page')
        total_pages = data.get('total_pages')
        progress_percentage = data.get('progress_percentage')
        completed = data.get('completed', False)

        if not lesson_id or current_page is None or total_pages is None:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        lesson = get_object_or_404(Lesson, id=lesson_id)
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={
                'current_page': 1,
                'total_pages': total_pages,
                'progress_percentage': 0,
                'completed': False
            }
        )

        progress.current_page = current_page
        progress.total_pages = total_pages
        progress.progress_percentage = progress_percentage
        if completed:
            progress.completed = True
        progress.save()

        return JsonResponse({
            'success': True,
            'current_page': progress.current_page,
            'progress_percentage': progress.progress_percentage,
            'completed': progress.completed
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ====== EXAM PARSING ======

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


# ====== EXAM AND WIZARD VIEWS ======

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
    """Learner takes an exam and is redirected to the result page."""
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
        else:
            create_notification(
                user=request.user,
                notification_type='exam_result',
                title='📝 Exam Result',
                message=f'You scored {percentage}% on "{exam.title}". You need {exam.passing_score}% to pass. Keep trying!',
                link=f'/courses/lesson/{lesson.id}/'
            )
        
        return redirect('exam_result', result_id=result.id)
    
    return render(request, 'courses/take_exam.html', {'exam': exam, 'lesson': lesson})


def exam_result(request, result_id):
    """Display the result of an exam."""
    result = get_object_or_404(ExamResult, id=result_id, user=request.user)
    return render(request, 'courses/exam_result.html', {'result': result})


# ========== EXAM MANAGEMENT FOR TEACHERS ==========

@upload_access
def add_fslc_papers(request):
    # Check if user has 'primary' in their levels
    if not request.user.profile.levels.filter(code='primary').exists():
        messages.error(request, "You are not authorized to add FSLC papers. Primary level required.")
        return redirect('lesson_list')
    
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        return redirect('add_exam', lesson_id=lesson_id)
    else:
        lessons = Lesson.objects.filter(teacher=request.user)
        return render(request, 'courses/select_lesson_for_exam.html', {'lessons': lessons, 'exam_type': 'FSLC'})


@upload_access
def add_mock_papers_primary(request):
    # Check if user has 'primary' in their levels
    if not request.user.profile.levels.filter(code='primary').exists():
        messages.error(request, "You are not authorized to add mock papers. Primary level required.")
        return redirect('lesson_list')
    
    lesson_id = request.GET.get('lesson_id')
    if lesson_id:
        return redirect('add_exam', lesson_id=lesson_id)
    else:
        lessons = Lesson.objects.filter(teacher=request.user)
        return render(request, 'courses/select_lesson_for_exam.html', {'lessons': lessons, 'exam_type': 'Mock (Primary)'})


@upload_access
def select_mock_exam_level(request):
    # Check if user has 'secondary' in their levels
    if not request.user.profile.levels.filter(code='secondary').exists():
        messages.error(request, "You are not authorized. Mock exams are only for secondary level teachers.")
        return redirect('lesson_list')
    return render(request, 'courses/select_mock_level.html')


@upload_access
def select_gce_level(request):
    # Check if user has 'secondary' in their levels
    if not request.user.profile.levels.filter(code='secondary').exists():
        messages.error(request, "You are not authorized. GCE questions are only for secondary level teachers.")
        return redirect('lesson_list')
    return render(request, 'courses/select_gce_level.html')


@upload_access
def add_mock_exam(request, level):
    # Check if user has 'secondary' in their levels
    if not request.user.profile.levels.filter(code='secondary').exists():
        messages.error(request, "You are not authorized to add mock exams. Secondary level required.")
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
    # Check if user has 'secondary' in their levels
    if not request.user.profile.levels.filter(code='secondary').exists():
        messages.error(request, "You are not authorized to add GCE past questions. Secondary level required.")
        return redirect('lesson_list')
    
    subjects = Subject.objects.all()
    years = range(2010, datetime.now().year + 1)
    context = {'level': level, 'subjects': subjects, 'years': years}
    
    if request.method == 'POST':
        year = request.POST.get('year')
        subject_id = request.POST.get('subject')
        subject = Subject.objects.get(id=subject_id) if subject_id else None
        
        # ----- DUPLICATE CHECK (no title, use year+subject+level) -----
        existing = Exam.objects.filter(
            year=year,
            subject_id=subject_id,
            level=level,
            exam_type='gce'
        ).exists()
        if existing:
            messages.error(request, "This exam paper already exists. Please check the year and subject.")
            return render(request, 'courses/add_gce_past_questions.html', context)
        # ---------------------------------------------------------------
        
        questions = None
        
        # 1) If a PDF file is uploaded, parse it
        if request.FILES.get('exam_pdf'):
            try:
                questions = parse_exam_file(request.FILES['exam_pdf'])
                if not questions:
                    messages.error(request, 'No questions could be parsed from the PDF. Please check the format.')
                    return render(request, 'courses/add_gce_past_questions.html', context)
            except Exception as e:
                messages.error(request, f'Error parsing PDF: {str(e)}')
                return render(request, 'courses/add_gce_past_questions.html', context)
        
        # 2) If no PDF, check for JSON input
        elif request.POST.get('questions'):
            questions_json = request.POST.get('questions')
            try:
                questions = json.loads(questions_json)
                if not isinstance(questions, list) or not questions:
                    messages.error(request, 'Invalid JSON format. Must be a non-empty array.')
                    return render(request, 'courses/add_gce_past_questions.html', context)
            except json.JSONDecodeError:
                messages.error(request, 'Invalid JSON format. Please check your syntax.')
                return render(request, 'courses/add_gce_past_questions.html', context)
        else:
            messages.error(request, 'Please either upload a PDF or provide questions in JSON format.')
            return render(request, 'courses/add_gce_past_questions.html', context)
        
        # ----- AUTO-GENERATE TITLE -----
        subject_name = subject.name if subject else "Unknown"
        title = f"GCE {level.title()} - {subject_name} ({year})"
        # ------------------------------
        
        # Create the exam
        exam = Exam(
            title=title,
            questions=questions,
            teacher=request.user,
            level=level,
            exam_type='gce',
            subject_id=subject_id if subject_id else None,
            year=year
        )
        exam.save()
        messages.success(request, f"GCE past questions '{title}' created successfully!")
        return redirect('lesson_list')
    
    return render(request, 'courses/add_gce_past_questions.html', context)


# ====== WIZARDS ======

@staff_member_required
def create_exam_wizard(request):
    if request.method == 'POST':
        form = ExamCreationForm(request.POST, request.FILES)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.exam_code = f"EXAM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            exam.status = 'pending'
            exam.save()
            
            if form.cleaned_data.get('exam_paper'):
                exam.exam_document = form.cleaned_data['exam_paper']
            if form.cleaned_data.get('marking_guide'):
                exam.marking_guide_document = form.cleaned_data['marking_guide']
            exam.save()
            
            messages.success(request, f"Exam '{exam.title}' created successfully!")
            return redirect('admin:courses_exam_changelist')
    else:
        form = ExamCreationForm()
    
    return render(request, 'courses/create_exam_wizard.html', {'form': form})


@staff_member_required
def issue_certificate_wizard(request):
    if request.method == 'POST':
        form = CertificateIssueForm(request.POST)
        if form.is_valid():
            achievement_type = form.cleaned_data['achievement_type']
            user = form.cleaned_data['user']
            lesson = form.cleaned_data.get('lesson')
            exam = form.cleaned_data.get('exam')
            issue_date = form.cleaned_data['issue_date']
            expiry_date = form.cleaned_data.get('expiry_date')
            custom_message = form.cleaned_data.get('custom_message')
            certificate_number = form.cleaned_data.get('certificate_number')

            if achievement_type == 'lesson' and lesson:
                certificate = Certificate.objects.create(
                    user=user,
                    lesson=lesson,
                    certificate_number=certificate_number,
                    issued_date=issue_date,
                )
                messages.success(request, f"Certificate issued to {user.username} for lesson '{lesson.title}'.")
                return redirect('admin:courses_certificate_changelist')

            elif achievement_type == 'exam' and exam:
                if hasattr(Certificate, 'exam'):
                    certificate = Certificate.objects.create(
                        user=user,
                        exam=exam,
                        certificate_number=certificate_number,
                        issued_date=issue_date,
                    )
                    messages.success(request, f"Certificate issued to {user.username} for exam '{exam.title}'.")
                elif exam.lesson:
                    certificate = Certificate.objects.create(
                        user=user,
                        lesson=exam.lesson,
                        certificate_number=certificate_number,
                        issued_date=issue_date,
                    )
                    messages.success(request, f"Certificate issued to {user.username} for exam '{exam.title}' (linked to lesson).")
                else:
                    messages.error(request, "This exam has no associated lesson. Cannot issue certificate.")
                    return render(request, 'courses/issue_certificate_wizard.html', {'form': form})

            else:
                messages.error(request, "Please select a valid achievement.")
                return render(request, 'courses/issue_certificate_wizard.html', {'form': form})

            return redirect('admin:courses_certificate_changelist')
    else:
        form = CertificateIssueForm()

    return render(request, 'courses/issue_certificate_wizard.html', {'form': form})


@staff_member_required
def create_course_wizard(request):
    if request.method == 'POST':
        form = CourseCreationForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.save()
            messages.success(request, f"Course '{course.name}' created successfully!")
            return redirect('admin:courses_course_changelist')
    else:
        form = CourseCreationForm()
    
    return render(request, 'courses/create_course_wizard.html', {'form': form})


# ====== CUSTOM ADMIN LESSON LIST VIEW ======

@staff_member_required
def admin_lesson_list(request):
    """
    Custom admin view for listing lessons, matching the style and functionality
    of the Students page (approve/reject/delete actions with checkboxes).
    """
    lessons = Lesson.objects.all().order_by('-created_at')
    total = lessons.count()

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_lessons')
        if selected_ids:
            lessons_selected = Lesson.objects.filter(id__in=selected_ids)
            if action == 'approve':
                lessons_selected.update(status='approved')
                messages.success(request, f"{lessons_selected.count()} lesson(s) approved.")
            elif action == 'reject':
                lessons_selected.update(status='rejected')
                messages.success(request, f"{lessons_selected.count()} lesson(s) rejected.")
            elif action == 'delete':
                lessons_selected.delete()
                messages.success(request, f"{len(selected_ids)} lesson(s) deleted.")
            else:
                messages.error(request, "Invalid action.")
        else:
            messages.error(request, "No lessons selected.")
        return redirect('admin:lesson_list')

    context = {
        'lessons': lessons,
        'total': total,
        'opts': Lesson._meta,
    }
    return render(request, 'admin/courses/lesson_list.html', context)


@login_required
def debug_lessons(request):
    """Temporary debug view to check lessons."""
    lessons = Lesson.objects.filter(teacher=request.user)
    output = f"Total lessons: {lessons.count()}\n"
    for l in lessons:
        output += f"ID: {l.id}, Title: {l.title}, Status: {l.status}\n"
    return HttpResponse(output, content_type='text/plain')