import os
import json
import re
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import JsonResponse
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
            # Blank line might separate questions
            if current_question and current_options:
                # If we have a question and options, finalize
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
        
        # Check for question number (e.g., "1.", "2)", etc.)
        question_match = re.match(r'^(\d+)[\.\)]\s*(.*)', line)
        if question_match:
            # If we have a previous question, save it
            if current_question and current_options:
                q = {
                    'question': current_question,
                    'options': current_options,
                    'correct': current_correct or (current_options[0] if current_options else "")
                }
                questions.append(q)
            # Start new question
            current_question = question_match.group(2).strip()
            current_options = []
            current_correct = None
            continue
        
        # Check for option (A., B., C., D.)
        option_match = re.match(r'^([A-D])[\.\)]\s*(.*)', line, re.IGNORECASE)
        if option_match and current_question is not None:
            option_text = option_match.group(2).strip()
            current_options.append(option_text)
            # Check if this option is marked as correct (e.g., has "*" or "(correct)" )
            if '*' in option_text or '(correct)' in option_text.lower():
                current_correct = option_text
            continue
        
        # Check for answer key line (e.g., "Answers: 1A, 2B, 3C")
        answer_match = re.match(r'^Answers?\s*[:;]\s*(.*)', line, re.IGNORECASE)
        if answer_match and questions:
            # We'll parse answer key and update correct answers for existing questions
            answer_key = answer_match.group(1).strip()
            # Split by commas or spaces
            parts = re.split(r'[,\s]+', answer_key)
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                # Try to extract number and letter
                num_letter = re.match(r'^(\d+)\s*([A-D])', part, re.IGNORECASE)
                if num_letter:
                    q_num = int(num_letter.group(1))
                    ans_letter = num_letter.group(2).upper()
                    if q_num <= len(questions):
                        # Map letter to option index
                        opt_idx = ord(ans_letter) - ord('A')
                        if opt_idx < len(questions[q_num-1]['options']):
                            questions[q_num-1]['correct'] = questions[q_num-1]['options'][opt_idx]
            continue
        
        # Otherwise, it's continuation of current question or option
        if current_question is not None:
            if current_options:
                # Append to last option
                current_options[-1] += " " + line
            else:
                # Append to question
                current_question += " " + line
    
    # Append last question
    if current_question and current_options:
        q = {
            'question': current_question,
            'options': current_options,
            'correct': current_correct or (current_options[0] if current_options else "")
        }
        questions.append(q)
    
    # If no questions found, try alternative format: each line is a question with options
    if not questions:
        # Fallback: assume each question is on a single line with options separated by semicolon
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Assume format: question? A: option A, B: option B, C: option C, D: option D
            # We'll attempt to split
            parts = re.split(r'[A-D]\s*[:.]\s*', line, flags=re.IGNORECASE)
            if len(parts) >= 2:
                question_text = parts[0].strip()
                options = [p.strip() for p in parts[1:] if p.strip()]
                if question_text and options:
                    questions.append({
                        'question': question_text,
                        'options': options,
                        'correct': options[0]  # placeholder
                    })
    
    return questions
@login_required
def add_exam(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    if request.user.profile.role != 'teacher':
        messages.error(request, 'Only teachers can add exams.')
        return redirect('home')
    
    if Exam.objects.filter(lesson=lesson).exists():
        messages.info(request, f'An exam already exists for "{lesson.title}".')
        return redirect('view_lesson', lesson_id=lesson.id)
    
    if request.method == 'POST':
        # Check if a file was uploaded
        exam_file = request.FILES.get('exam_file')
        json_questions = request.POST.get('questions')
        title = request.POST.get('title')
        passing_score = request.POST.get('passing_score', 50)
        
        questions = None
        if exam_file:
            # Parse the file
            try:
                questions = parse_exam_file(exam_file)
                if not questions:
                    messages.error(request, 'No questions could be parsed from the file. Please check the format.')
                    return render(request, 'courses/add_exam.html', {'lesson': lesson})
            except Exception as e:
                messages.error(request, f'Error parsing file: {e}')
                return render(request, 'courses/add_exam.html', {'lesson': lesson})
        elif json_questions:
            # Use JSON input
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
        
        # Create the exam
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
    
    return render(request, 'courses/add_exam.html', {'lesson': lesson})@login_required
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