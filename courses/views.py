import os
import json
import re
import tempfile
import urllib.parse
from datetime import datetime, timedelta

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Users & notifications
from users.utils import create_notification
from users.models import Wishlist
from users.decorators import basic_access, lesson_access, upload_access

# Cloudinary
import cloudinary
import cloudinary.api
import requests
from cloudinary.utils import cloudinary_url

# Forms and models
from .forms import LessonForm, ExamForm, ExamCreationForm, CertificateIssueForm, CourseCreationForm
from .models import Subject, Lesson, Progress, Exam, ExamResult, Certificate, Course, LessonProgress
from .utils import convert_uploaded_file_to_pdf

# ====== WHITEBOARD VIDEO CONVERSION (uses pypdfium2 + moviepy) ======
import pypdfium2 as pdfium
from moviepy.editor import ImageSequenceClip


@login_required
def convert_lesson_to_whiteboard(request, lesson_id):
    """
    Convert a lesson's PDF to a whiteboard video using Cloudinary API.
    Falls back to a signed URL if the API fails (fixes 401).
    """
    lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)

    if not lesson.pdf_file:
        messages.error(request, "This lesson has no PDF to convert.")
        return redirect('view_lesson', lesson_id=lesson.id)

    # Get the public ID (remove extension)
    public_id = lesson.pdf_file.name
    if '.' in public_id:
        public_id = public_id.rsplit('.', 1)[0]

    if not public_id:
        messages.error(request, "Could not determine public ID for PDF.")
        return redirect('view_lesson', lesson_id=lesson.id)

    download_url = None
    error_msg = ""

    # 1️⃣ Try Cloudinary API first (resource_type='raw')
    try:
        resource = cloudinary.api.resource(public_id, resource_type='raw')
        download_url = resource.get('secure_url')
        if download_url:
            messages.info(request, "Using Cloudinary API (raw).")
    except cloudinary.exceptions.NotFound:
        try:
            # Fallback to 'image'
            resource = cloudinary.api.resource(public_id, resource_type='image')
            download_url = resource.get('secure_url')
            if download_url:
                messages.info(request, "Using Cloudinary API (image).")
        except cloudinary.exceptions.NotFound:
            error_msg = "PDF not found via API. Trying signed URL..."
    except cloudinary.exceptions.Error as e:
        error_msg = f"Cloudinary API error: {str(e)}"

    # 2️⃣ If API fails, generate a signed URL
    if not download_url:
        try:
            # Try as raw first
            signed_url, _ = cloudinary_url(
                public_id,
                resource_type='raw',
                sign_url=True,
                flags='attachment',
                expires_at=int((datetime.now().timestamp() + 300))  # 5 min
            )
            # Test with a HEAD request
            test_response = requests.head(signed_url)
            if test_response.status_code == 200:
                download_url = signed_url
                messages.info(request, "Using signed URL (raw).")
            else:
                # Try as image
                signed_url, _ = cloudinary_url(
                    public_id,
                    resource_type='image',
                    sign_url=True,
                    flags='attachment',
                    expires_at=int((datetime.now().timestamp() + 300))
                )
                test_response = requests.head(signed_url)
                if test_response.status_code == 200:
                    download_url = signed_url
                    messages.info(request, "Using signed URL (image).")
                else:
                    error_msg = f"Signed URL test failed (HTTP {test_response.status_code})"
        except Exception as e:
            error_msg = f"Signed URL generation failed: {str(e)}"

    if not download_url:
        messages.error(request, f"Could not retrieve PDF: {error_msg}")
        return redirect('view_lesson', lesson_id=lesson.id)

    # 3️⃣ Download the PDF
    try:
        response = requests.get(download_url)
        if response.status_code != 200:
            messages.error(request, f"Download failed (HTTP {response.status_code}).")
            return redirect('view_lesson', lesson_id=lesson.id)

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf.write(response.content)
            tmp_pdf_path = tmp_pdf.name

    except Exception as e:
        messages.error(request, f"Download error: {str(e)}")
        return redirect('view_lesson', lesson_id=lesson.id)

    # 4️⃣ Convert PDF to video
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            pdf = pdfium.PdfDocument(tmp_pdf_path)
            image_paths = []
            for i in range(len(pdf)):
                page = pdf.get_page(i)
                bitmap = page.render(scale=2.0)
                pil_image = bitmap.to_pil()
                img_path = os.path.join(tmpdir, f"page_{i+1}.jpeg")
                pil_image.save(img_path, 'JPEG')
                image_paths.append(img_path)

            if not image_paths:
                messages.error(request, "Could not extract pages from the PDF.")
                return redirect('view_lesson', lesson_id=lesson.id)

            clip = ImageSequenceClip(image_paths, fps=0.5)
            video_path = os.path.join(tmpdir, 'whiteboard_video.mp4')
            clip.write_videofile(video_path, fps=24, codec='libx264', audio=False)

            with open(video_path, 'rb') as f:
                lesson.whiteboard_video.save(f"whiteboard_{lesson.id}.mp4", ContentFile(f.read()), save=True)

            messages.success(request, "✅ Whiteboard video created successfully!")
        except Exception as e:
            messages.error(request, f"Conversion failed: {str(e)}")
        finally:
            if os.path.exists(tmp_pdf_path):
                os.unlink(tmp_pdf_path)

    return redirect('view_lesson', lesson_id=lesson.id)


# ====== Core Lesson Views ======

@basic_access
def lesson_list(request):
    """Display lessons – learners see only their level, teachers see all."""
    lessons = Lesson.objects.filter(status='approved').order_by('-created_at')
    
    if request.user.is_authenticated and request.user.profile.role == 'learner':
        lessons = lessons.filter(level=request.user.profile.level)
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


@upload_access
def upload_lesson(request):
    """Teachers upload a new lesson – level is forced to teacher's level, with Word to PDF conversion."""
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can upload lessons.')
        return redirect('home')

    teacher_level = request.user.profile.level

    if not teacher_level:
        messages.error(request, 'Please set your education level in your profile before uploading a lesson.')
        return redirect('profile')

    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if 'level' in form.fields:
            del form.fields['level']
        
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.teacher = request.user
            lesson.status = 'pending'
            lesson.level = teacher_level

            # --- Handle new subject creation ---
            selected_subject_id = request.POST.get('subject')
            new_subject_name = request.POST.get('new_subject_name', '').strip()
            new_subject_code = request.POST.get('new_subject_code', '').strip()

            # If a subject is selected from dropdown, use it
            if selected_subject_id:
                try:
                    lesson.subject = Subject.objects.get(id=selected_subject_id)
                except Subject.DoesNotExist:
                    messages.error(request, 'Selected subject does not exist.')
                    return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
            elif new_subject_name:
                # Check if subject already exists (case‑insensitive)
                existing = Subject.objects.filter(name__iexact=new_subject_name, level=teacher_level).first()
                if existing:
                    lesson.subject = existing
                    messages.info(request, f'Using existing subject "{existing.name}".')
                else:
                    # Create new subject with code
                    subject = Subject.objects.create(
                        name=new_subject_name,
                        code=new_subject_code,
                        level=teacher_level,
                        proposed_by=request.user,
                        status='pending'
                    )
                    lesson.subject = subject
                    messages.success(request, f'New subject "{subject.name}" created and pending approval.')
            # If no subject selected and no new name, lesson.subject will remain None

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
                        return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
                else:
                    lesson.pdf_file = uploaded_file
                    lesson.is_converted = False

            # Validate subject/course based on level
            if lesson.level in ['primary', 'secondary'] and not lesson.subject:
                messages.error(request, 'Please select a subject or create a new one for primary/secondary level.')
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
            return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
    else:
        form = LessonForm()
        if 'level' in form.fields:
            del form.fields['level']

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


# ====== NEW PDF READER WITH PROGRESS ======

@xframe_options_exempt
@lesson_access
def view_lesson(request, lesson_id):
    """New PDF reader view with progress tracking."""
    from .models import LessonProgress
    from datetime import timedelta
    import cloudinary.utils

    lesson = get_object_or_404(Lesson, id=lesson_id)
    exam = None

    # Get or create progress
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
            public_id = lesson.pdf_file.name
            if '.' in public_id:
                public_id = public_id.rsplit('.', 1)[0]

            # Calculate expiry timestamp (1 hour from now)
            expires_at = int((datetime.now() + timedelta(hours=1)).timestamp())
            print(f"DEBUG: public_id = {public_id}, expires_at = {expires_at}")

            # Try as image first
            signed_url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type='image',
                type='upload',          # explicitly set
                sign_url=True,
                expires_at=expires_at
            )[0]

            # If the URL still contains 's--', it's a transformation signature,
            # not a delivery signature – try 'raw' as fallback.
            if 's--' in signed_url:
                print("DEBUG: image URL has transformation signature, trying raw...")
                signed_url = cloudinary.utils.cloudinary_url(
                    public_id,
                    resource_type='raw',
                    type='upload',
                    sign_url=True,
                    expires_at=expires_at
                )[0]

            pdf_url = signed_url
            print(f"DEBUG: Final PDF URL: {pdf_url}")

        except Exception as e:
            pdf_url = None
            messages.warning(request, f"Could not generate PDF URL: {str(e)}")
            print(f"ERROR: {e}")

    context = {
        'lesson': lesson,
        'exam': exam,
        'pdf_url': pdf_url,
        'progress': progress,
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
        action = request.POST.get('action')          # 'approve', 'reject', 'delete'
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
        # Redirect back to this same view
        return redirect('admin:lesson_list')   # This name will be registered in core/admin.py

    context = {
        'lessons': lessons,
        'total': total,
        'opts': Lesson._meta,   # for breadcrumbs
    }
    return render(request, 'admin/courses/lesson_list.html', context)// Force redeploy 
