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
        paper_number = request.POST.get('paper_number')  # <-- NEW
        subject = Subject.objects.get(id=subject_id) if subject_id else None
        
        # ----- DUPLICATE CHECK (include paper_number) -----
        existing = Exam.objects.filter(
            year=year,
            subject_id=subject_id,
            level=level,
            paper_number=paper_number,  # <-- NEW
            exam_type='gce'
        ).exists()
        if existing:
            messages.error(request, "This exam paper already exists. Please check the year, subject, and paper number.")
            return render(request, 'courses/add_gce_past_questions.html', context)
        # ----------------------------------------------------
        
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
        
        # ----- AUTO-GENERATE TITLE (include paper number) -----
        subject_name = subject.name if subject else "Unknown"
        title = f"GCE {level.title()} - {subject_name} ({year}) - Paper {paper_number}"
        # ----------------------------------------------------
        
        # Create the exam
        exam = Exam(
            title=title,
            questions=questions,
            teacher=request.user,
            level=level,
            exam_type='gce',
            subject_id=subject_id if subject_id else None,
            year=year,
            paper_number=paper_number  # <-- NEW
        )
        exam.save()
        messages.success(request, "✅ Exam saved! Learners can now access this paper.")
        return redirect('lesson_list')
    
    return render(request, 'courses/add_gce_past_questions.html', context)