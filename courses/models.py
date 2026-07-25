from django.db import models
from django.contrib.auth.models import User
from users.models import UserProfile
from cloudinary.models import CloudinaryField
import uuid

# ===== Status choices (shared across models) =====
STATUS_CHOICES = (
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
)


class Subject(models.Model):
    """For primary and secondary school subjects (e.g., Mathematics, English)"""
    LEVEL_CHOICES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
    )
    STATUS_CHOICES = STATUS_CHOICES

    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Subject code (e.g., MATH101, PHY201)"
    )
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    description = models.TextField(blank=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, default='', help_text="Notes from admin")
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_subjects'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    proposed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='proposed_subjects'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class Course(models.Model):
    STATUS_CHOICES = STATUS_CHOICES

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Lesson(models.Model):
    LEVEL_CHOICES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('university', 'University / Higher Institution'),
    )
    STATUS_CHOICES = STATUS_CHOICES

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'status': 'approved'},
        help_text="Only approved subjects can be used."
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)

    pdf_file = CloudinaryField(
        'PDF',
        resource_type='raw',
        null=True,
        blank=True,
        help_text="Upload PDF lesson"
    )
    original_file = models.FileField(upload_to='lessons/originals/', blank=True, null=True, help_text="Original uploaded file (for Word documents)")
    is_converted = models.BooleanField(default=False, help_text="True if this lesson was converted from a Word document")
    converted_html = models.TextField(blank=True, help_text="System will convert PDF to HTML for web view")
    video_url = models.URLField(max_length=500, blank=True, help_text="YouTube or Vimeo link")
    video_file = models.FileField(upload_to='lessons/videos/', null=True, blank=True, help_text="Upload video file")

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'profile__role': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.IntegerField(default=0)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, default='', help_text="Admin notes for review")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_lessons')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    @property
    def pdf_url(self):
        if self.pdf_file:
            return self.pdf_file.url.replace('image/upload', 'raw/upload')
        return None

    def get_engagement_stats(self):
        likes_count = self.likes.count()
        comments_count = self.comments.count()
        return {
            'likes': likes_count,
            'comments': comments_count,
            'views': self.views,
            'engagement_score': likes_count + comments_count,
        }

    def __str__(self):
        return self.title


class Progress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    progress_percentage = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(auto_now=True)
    pages_read = models.IntegerField(default=0)
    total_pages = models.IntegerField(default=0)

    class Meta:
        unique_together = ('user', 'lesson')
        verbose_name_plural = "Progress"

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} ({self.progress_percentage}%)"


class Exam(models.Model):
    # ===== Shared status choices =====
    STATUS_CHOICES = STATUS_CHOICES

    # ===== Exam Information =====
    title = models.CharField(max_length=200)
    course = models.ForeignKey('Course', on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='exams')
    exam_type = models.CharField(max_length=50, choices=(
        ('quiz', 'Quiz'),
        ('class_test', 'Class Test'),
        ('assignment', 'Assignment'),
        ('ca', 'Continuous Assessment (CA)'),
        ('practical', 'Practical Test'),
        ('mock', 'Mock Exam'),
        ('mid_term', 'Mid-Term Examination'),
        ('end_term', 'End-of-Term Examination'),
        ('final', 'Final Examination'),
        ('entrance', 'Entrance Examination'),
        ('certification', 'Certification Exam'),
    ), default='quiz')
    academic_session = models.CharField(max_length=20, choices=(
        ('2025/2026', '2025/2026'),
        ('2026/2027', '2026/2027'),
        ('2027/2028', '2027/2028'),
    ), blank=True, null=True)
    term = models.CharField(max_length=20, choices=(
        ('first', 'First Term'),
        ('second', 'Second Term'),
        ('third', 'Third Term'),
        ('semester_1', 'Semester I'),
        ('semester_2', 'Semester II'),
    ), blank=True, null=True)
    # ===== UPDATED: Level choices to school levels =====
    level = models.CharField(max_length=20, choices=(
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('higher', 'Higher Institution / University'),
    ), blank=True, null=True)
    exam_code = models.CharField(max_length=50, blank=True, editable=False)
    language = models.CharField(max_length=10, choices=(('en', 'English'), ('fr', 'French')), default='en')
    duration_minutes = models.PositiveIntegerField(default=60, help_text="Duration in minutes")
    total_marks = models.PositiveIntegerField(default=100)
    passing_score = models.PositiveIntegerField(default=50, help_text="Percentage required to pass")
    number_of_questions = models.PositiveIntegerField(null=True, blank=True, help_text="Optional, auto-calculated if left blank")
    instructions = models.TextField(blank=True, help_text="Instructions to students (supports HTML)")

    # ===== Availability =====
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Time limit for the exam, in minutes")
    attempts_allowed = models.PositiveIntegerField(default=1, help_text="Number of attempts allowed")
    question_order = models.CharField(max_length=10, choices=(('fixed', 'Fixed'), ('random', 'Randomized')), default='fixed')
    answer_order = models.CharField(max_length=10, choices=(('fixed', 'Fixed'), ('random', 'Randomized')), default='fixed')
    show_result_immediately = models.BooleanField(default=True)
    show_correct_answers = models.CharField(max_length=20, choices=(
        ('immediately', 'Immediately'),
        ('after_due', 'After Due Date'),
        ('never', 'Never'),
    ), default='immediately')
    auto_submit = models.BooleanField(default=False)
    late_submission = models.BooleanField(default=False, help_text="Allow late submission")

    # ===== Access Control =====
    visibility = models.CharField(max_length=20, choices=(
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ), default='draft')
    require_password = models.BooleanField(default=False)
    exam_password = models.CharField(max_length=50, blank=True, help_text="Password required to access the exam")
    require_safe_browser = models.BooleanField(default=False)
    require_webcam = models.BooleanField(default=False)
    randomize_questions = models.BooleanField(default=False)

    # ===== Grading =====
    grading_method = models.CharField(max_length=20, choices=(
        ('highest', 'Highest Score'),
        ('latest', 'Latest Attempt'),
        ('average', 'Average Score'),
    ), default='highest')
    negative_marking = models.BooleanField(default=False)
    marks_per_question = models.CharField(max_length=10, choices=(('auto', 'Automatic'), ('manual', 'Manual')), default='auto')
    auto_grade_objective = models.BooleanField(default=True)
    manual_review_required = models.BooleanField(default=False)

    # ===== Exam Source (new) =====
    EXAM_SOURCE_CHOICES = (
        ('online', 'Create Online Exam'),
        ('document', 'Upload Exam Document'),
        ('import', 'Import Question Bank'),
    )
    exam_source = models.CharField(max_length=10, choices=EXAM_SOURCE_CHOICES, default='online')
    exam_document = models.FileField(upload_to='exams/documents/', blank=True, null=True, help_text="Upload exam paper (PDF/DOC/DOCX)")
    marking_guide_document = models.FileField(upload_to='exams/marking_guides/', blank=True, null=True, help_text="Upload marking guide (PDF/DOC/DOCX)")

    # ===== Additional Resources =====
    additional_resources = models.FileField(upload_to='exams/resources/', blank=True, null=True)

    # ===== Anti-cheating =====
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    fullscreen_mode = models.BooleanField(default=False)
    disable_copy_paste = models.BooleanField(default=False)
    browser_lock = models.BooleanField(default=False)
    webcam_monitoring = models.BooleanField(default=False)
    screen_recording = models.BooleanField(default=False)
    tab_switching_detection = models.BooleanField(default=False)
    ip_restriction = models.BooleanField(default=False)

    # ===== Notifications =====
    notify_immediately = models.BooleanField(default=True)
    notify_on_publish = models.BooleanField(default=True)
    notify_before_deadline = models.BooleanField(default=False)
    notify_after_grading = models.BooleanField(default=True)

    # ===== Legacy fields (keep for compatibility) =====
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='exams', null=True, blank=True)
    passing_score_old = models.IntegerField(default=50)
    questions = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    exam_type_old = models.CharField(max_length=20, blank=True, null=True)
    year = models.CharField(max_length=4, blank=True, null=True)
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams_created')
    marking_guide = models.TextField(blank=True, help_text="Teaching guide with suggested answers and explanations")

    # ===== Approval workflow =====
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, default='', help_text="Admin notes for review")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_exams')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.exam_code:
            import hashlib
            import time
            raw = f"{self.title}{time.time()}"
            self.exam_code = hashlib.md5(raw.encode()).hexdigest()[:10].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.get_exam_type_display()})"


class ExamResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField()
    percentage = models.IntegerField()
    passed = models.BooleanField(default=False)
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.exam.title} - {self.percentage}%"


class Certificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, null=True, blank=True)
    certificate_number = models.CharField(max_length=100, unique=True, editable=False)
    issued_date = models.DateTimeField(auto_now_add=True)
    score = models.IntegerField()

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = f"CERT-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Certificate for {self.user.username} - {self.lesson.title if self.lesson else self.exam.title}"


# ===== Social Features =====

class LessonLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f"{self.user.username} likes {self.lesson.title}"


class ExamLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'exam')

    def __str__(self):
        return f"{self.user.username} likes {self.exam.title}"


class LessonComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"


class ExamComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"