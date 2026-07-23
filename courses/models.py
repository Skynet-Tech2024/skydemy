from django.db import models
from django.contrib.auth.models import User
from users.models import UserProfile
from cloudinary.models import CloudinaryField
import uuid

class Subject(models.Model):
    """For primary and secondary school subjects (e.g., Mathematics, English)"""
    LEVEL_CHOICES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
    )
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"

class Course(models.Model):
    """For university courses (e.g., CS101, Physics 201)"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Lesson(models.Model):
    LEVEL_CHOICES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('university', 'University / Higher Institution'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    
    # For primary/secondary -> select a Subject
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    
    # For university -> select a Course
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    
    # PDF file stored on Cloudinary
    pdf_file = CloudinaryField(
        'PDF',
        resource_type='raw',          # Allows any file type
        null=True,
        blank=True,
        help_text="Upload PDF lesson"
    )
    
    original_file = models.FileField(upload_to='lessons/originals/', blank=True, null=True, help_text="Original uploaded file (for Word documents)")
    is_converted = models.BooleanField(default=False, help_text="True if this lesson was converted from a Word document")
    converted_html = models.TextField(blank=True, help_text="System will convert PDF to HTML for web view")
    video_url = models.URLField(max_length=500, blank=True, help_text="YouTube or Vimeo link")
    video_file = models.FileField(upload_to='lessons/videos/', null=True, blank=True, help_text="Upload video file")
    
    # Teacher who uploaded this lesson
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'profile__role': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Engagement fields
    views = models.IntegerField(default=0)
    
    # Approval workflow
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes for review")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_lessons')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # ----- NEW: Property to get correct PDF URL -----
    @property
    def pdf_url(self):
        """Return the Cloudinary URL with 'raw/upload' instead of 'image/upload'."""
        if self.pdf_file:
            return self.pdf_file.url.replace('image/upload', 'raw/upload')
        return None
    # ------------------------------------------------
    
    def get_engagement_stats(self):
        """Return engagement statistics for this lesson"""
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
    """Tracks student reading progress for each lesson"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    progress_percentage = models.IntegerField(default=0)  # 0-100
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(auto_now=True)
    pages_read = models.IntegerField(default=0)  # For PDF page tracking
    total_pages = models.IntegerField(default=0)  # Total pages in the PDF
    
    class Meta:
        unique_together = ('user', 'lesson')
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} ({self.progress_percentage}%)"

class Exam(models.Model):
    """Exam associated with a lesson"""
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=200)
    passing_score = models.IntegerField(default=50)
    questions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    # New fields for exam management
    exam_type = models.CharField(max_length=20, choices=(
        ('fslc', 'FSLC Papers'),
        ('mock', 'Mock Exam'),
        ('gce', 'GCE Past Questions'),
    ), blank=True, null=True)
    
    year = models.CharField(max_length=4, blank=True, null=True)  # For GCE
    level = models.CharField(max_length=20, blank=True, null=True)  # ordinary/advanced
    subject = models.ForeignKey('Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='exams')
    teacher = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='exams_created')
    # Teaching guide / marking guide
    marking_guide = models.TextField(blank=True, help_text="Teaching guide with suggested answers and explanations")
    
    # Approval workflow
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, help_text="Admin notes for review")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_exams')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def get_engagement_stats(self):
        """Return engagement statistics for this exam"""
        likes_count = self.likes.count()
        comments_count = self.comments.count()
        return {
            'likes': likes_count,
            'comments': comments_count,
            'engagement_score': likes_count + comments_count,
        }
    
    def __str__(self):
        return f"{self.title} - {self.lesson.title}"

class ExamResult(models.Model):
    """Student's exam attempt result"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField()
    percentage = models.IntegerField()
    passed = models.BooleanField(default=False)
    date_taken = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.exam.title} - {self.percentage}%"

class Certificate(models.Model):
    """Auto-generated certificate after passing an exam"""
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

# ===== Social Features: Likes and Comments =====

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