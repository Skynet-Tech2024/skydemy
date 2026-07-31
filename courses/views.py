from django.template.loader import get_template   # Add this import at the top

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

            if selected_subject_id:
                try:
                    lesson.subject = Subject.objects.get(id=selected_subject_id)
                except Subject.DoesNotExist:
                    messages.error(request, 'Selected subject does not exist.')
                    return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
            elif new_subject_name:
                existing = Subject.objects.filter(name__iexact=new_subject_name, level=teacher_level).first()
                if existing:
                    lesson.subject = existing
                    messages.info(request, f'Using existing subject "{existing.name}".')
                else:
                    subject = Subject.objects.create(
                        name=new_subject_name,
                        code=new_subject_code,
                        level=teacher_level,
                        proposed_by=request.user,
                        status='pending'
                    )
                    lesson.subject = subject
                    messages.success(request, f'New subject "{subject.name}" created and pending approval.')

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

            if lesson.level in ['primary', 'secondary'] and not lesson.subject:
                messages.error(request, 'Please select a subject or create a new one for primary/secondary level.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})
            if lesson.level == 'university' and not lesson.course:
                messages.error(request, 'Please select a course for university level.')
                return render(request, 'courses/upload_lesson.html', {'form': form, 'teacher_level': teacher_level})

            lesson.save()

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

    # Debug: log the template being rendered and check if it exists
    template_name = 'courses/upload_lesson.html'
    print(f"Rendering template: {template_name}")
    try:
        template = get_template(template_name)
        print(f"Template loaded successfully from: {template.origin.name}")
    except Exception as e:
        print(f"Template load error: {e}")

    return render(request, template_name, {'form': form, 'teacher_level': teacher_level})