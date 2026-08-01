from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# ===== CHOICES =====
LEVEL_CHOICES = [
    ('primary', 'Primary'),
    ('secondary', 'Secondary'),
    ('technical', 'Technical & Vocational'),
    ('university', 'University'),
    ('higher', 'Higher Institute'),
    ('professional', 'Professional Certification'),
    ('other', 'Other'),
]

CYCLE_CHOICES = [
    ('first', 'First Cycle'),
    ('second', 'Second Cycle'),
]

CLASS_CHOICES = [
    ('form3', 'Form 3'),
    ('form4', 'Form 4'),
    ('form5', 'Form 5'),
    ('lower_sixth', 'Lower Sixth'),
    ('upper_sixth', 'Upper Sixth'),
]

# ===== DEPARTMENT =====
class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name

# ===== SUBJECT =====
class Subject(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='primary')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    proposed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# ===== COURSE =====
class Course(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
    )

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# ===== LESSON =====
class Lesson(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    title = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='primary')
    description = models.TextField(blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='lessons', null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons', null=True, blank=True)
    pdf_file = models.FileField(upload_to='lessons/pdfs/', blank=True, null=True)
    original_file = models.FileField(upload_to='lessons/originals/', blank=True, null=True)
    is_converted = models.BooleanField(default=False)
    converted_html = models.TextField(blank=True)
    video_url = models.URLField(blank=True, null=True)
    video_file = models.FileField(upload_to='lessons/videos/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lessons')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_lessons')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)

    # Whiteboard video
    whiteboard_video = models.FileField(
        upload_to='lessons/whiteboard_videos/',
        blank=True,
        null=True,
        help_text="Generated whiteboard video from the PDF."
    )

    # Academic hierarchy fields
    cycle = models.CharField(max_length=10, choices=CYCLE_CHOICES, blank=True, null=True)
    class_level = models.CharField(max_length=15, choices=CLASS_CHOICES, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

# ===== LESSON LIKE =====
class LessonLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_likes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user.username} likes {self.lesson.title}"

# ===== LESSON COMMENT =====
class LessonComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_comments')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.lesson.title}"

# ===== PROGRESS =====
class Progress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    progress_percentage = models.PositiveSmallIntegerField(default=0)
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')
        ordering = ['-last_accessed']

# ===== LESSON PROGRESS (for reader) =====
class LessonProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='user_progress')

    current_page = models.IntegerField(default=1)
    total_pages = models.IntegerField(default=1)
    progress_percentage = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} ({self.progress_percentage}%)"

# ===== EXAM =====
class Exam(models.Model):
    EXAM_TYPES = (
        ('quiz', 'Quiz'),
        ('exam', 'Exam'),
        ('final', 'Final'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published'),
    )
    VISIBILITY_CHOICES = (
        ('public', 'Public'),
        ('private', 'Private'),
        ('registered', 'Registered Only'),
    )
    GRADING_METHODS = (
        ('manual', 'Manual'),
        ('auto', 'Automatic'),
        ('hybrid', 'Hybrid'),
    )

    title = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default='exam')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='exams', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams', null=True, blank=True)
    academic_session = models.CharField(max_length=50, blank=True, null=True)
    term = models.CharField(max_length=50, blank=True, null=True)
    level = models.CharField(max_length=50, blank=True, null=True)
    language = models.CharField(max_length=50, default='English')
    exam_code = models.CharField(max_length=20, unique=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    total_marks = models.PositiveIntegerField(default=100)
    passing_score = models.PositiveIntegerField(default=40)
    number_of_questions = models.PositiveIntegerField(default=10)
    instructions = models.TextField(blank=True)

    # Availability
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    attempts_allowed = models.PositiveIntegerField(default=1)
    question_order = models.CharField(max_length=20, default='sequential')
    answer_order = models.CharField(max_length=20, default='sequential')
    show_result_immediately = models.BooleanField(default=False)
    show_correct_answers = models.BooleanField(default=False)
    auto_submit = models.BooleanField(default=True)
    late_submission = models.BooleanField(default=False)

    # Access Control
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    require_password = models.BooleanField(default=False)
    exam_password = models.CharField(max_length=50, blank=True, null=True)
    require_safe_browser = models.BooleanField(default=False)
    require_webcam = models.BooleanField(default=False)
    randomize_questions = models.BooleanField(default=False)

    # Grading
    grading_method = models.CharField(max_length=20, choices=GRADING_METHODS, default='auto')
    negative_marking = models.BooleanField(default=False)
    marks_per_question = models.PositiveIntegerField(default=1)
    auto_grade_objective = models.BooleanField(default=True)
    manual_review_required = models.BooleanField(default=False)

    # Anti-cheating
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    fullscreen_mode = models.BooleanField(default=False)
    disable_copy_paste = models.BooleanField(default=False)
    browser_lock = models.BooleanField(default=False)
    webcam_monitoring = models.BooleanField(default=False)
    screen_recording = models.BooleanField(default=False)
    tab_switching_detection = models.BooleanField(default=False)
    ip_restriction = models.BooleanField(default=False)

    # Notifications
    notify_immediately = models.BooleanField(default=False)
    notify_on_publish = models.BooleanField(default=False)
    notify_before_deadline = models.BooleanField(default=False)
    notify_after_grading = models.BooleanField(default=False)

    # Approval Workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_exams')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_exams')

    # File upload fields
    exam_document = models.FileField(upload_to='exams/documents/', blank=True, null=True)
    marking_guide_document = models.FileField(upload_to='exams/marking_guides/', blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']

# ===== EXAM RESULT =====
class ExamResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_results')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    score = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    passed = models.BooleanField(default=False)
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"

    class Meta:
        ordering = ['-date_taken']

# ===== CERTIFICATE =====
class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='certificates', null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, null=True, blank=True, related_name='certificates')
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_date = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(default=0.0)  # Score achieved

    def __str__(self):
        return f"Certificate #{self.certificate_number} - {self.user.username}"