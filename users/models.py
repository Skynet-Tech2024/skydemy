from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('teacher', 'Teacher'),
        ('learner', 'Learner'),
    )
    
    LEVEL_CHOICES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('university', 'University / Higher Institution'),
    )
    
    VERIFICATION_CHOICES = (
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='learner')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='primary')  # Now required with default
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True, help_text="Optional WhatsApp number for announcements")  # New
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_lessons_completed = models.IntegerField(default=0)
    is_premium = models.BooleanField(default=False, help_text="Premium subscription for PDF downloads")
    subscription_expiry = models.DateTimeField(null=True, blank=True, help_text="When premium subscription expires")
    verification_status = models.CharField(max_length=10, choices=VERIFICATION_CHOICES, default='pending')
    verification_notes = models.TextField(blank=True, help_text="Admin notes for verification")
    last_active = models.DateTimeField(null=True, blank=True, help_text="Last time the user was active")
    is_suspended = models.BooleanField(default=False, help_text="Manually suspend this user")
    
    # Profile picture
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, default='avatars/default.png')
    
    def get_status(self):
        if self.is_suspended:
            return 'Suspended'
        if self.verification_status == 'pending':
            return 'Pending'
        if self.verification_status == 'rejected':
            return 'Rejected'
        if self.last_active:
            days_inactive = (timezone.now() - self.last_active).days
            if days_inactive > 90:
                return 'Inactive'
        return 'Active'
    
    def get_avatar_url(self):
        """Return the avatar URL or a default if not set"""
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return '/static/images/default-avatar.png'  # Fallback to a static default
    
    def calculate_rating(self):
        """Calculate rating based on likes, comments, and views of user's lessons"""
        from courses.models import Lesson, LessonLike, LessonComment
        from django.db.models import Sum, Count
        
        # Get all lessons by this teacher
        lessons = Lesson.objects.filter(teacher=self.user)
        if not lessons.exists():
            return 0.0
        
        total_likes = LessonLike.objects.filter(lesson__in=lessons).count()
        total_comments = LessonComment.objects.filter(lesson__in=lessons).count()
        total_views = lessons.aggregate(Sum('views'))['views__sum'] or 0
        
        engagement_score = total_likes + total_comments
        if total_views > 0:
            rating = (engagement_score / total_views) * 5
        else:
            rating = 0
        
        return min(round(rating, 2), 5.0)
    
    def update_rating(self):
        """Update the rating field with the calculated value"""
        self.rating = self.calculate_rating()
        self.save(update_fields=['rating'])
    
    def get_rating_display(self):
        """Return rating as stars with percentage"""
        if self.rating == 0:
            return "⭐ 0.00 (0%)"
        percentage = (self.rating / 5) * 100
        full_stars = int(self.rating)
        half_star = 1 if self.rating - full_stars >= 0.5 else 0
        stars = '★' * full_stars + ('½' if half_star else '')
        empty_stars = '☆' * (5 - full_stars - half_star)
        return f"{stars}{empty_stars} {self.rating:.2f} ({percentage:.0f}%)"
    
    def get_display_role(self):
        """Return display role: 'Admin' for superusers/staff, otherwise the actual role"""
        if self.user.is_superuser or self.user.is_staff:
            return 'Admin'
        return self.get_role_display()
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('lesson_approved', 'Lesson Approved'),
        ('exam_result', 'Exam Result'),
        ('certificate_earned', 'Certificate Earned'),
        ('system', 'System Notification'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='system')
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.URLField(blank=True, null=True, help_text="Optional link to redirect when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.created_at})"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers', limit_choices_to={'profile__role': 'teacher'})
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'following')
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'lesson')
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"


class ProgressHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_history')
    total_lessons_completed = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['recorded_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.total_lessons_completed} lessons - {self.recorded_at.strftime('%Y-%m-%d %H:%M')}"


class WhatsAppAnnouncement(models.Model):
    TARGET_CHOICES = (
        ('all', 'All Users'),
        ('teachers', 'Teachers Only'),
        ('learners', 'Learners Only'),
        ('premium', 'Premium Users'),
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='all')
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_announcements')
    sent_at = models.DateTimeField(auto_now_add=True)
    is_sent = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "WhatsApp Announcement"
        verbose_name_plural = "WhatsApp Announcements"
    
    def __str__(self):
        return f"{self.title} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_recipients(self):
        from users.models import UserProfile
        if self.target == 'all':
            return User.objects.all()
        elif self.target == 'teachers':
            return User.objects.filter(profile__role='teacher')
        elif self.target == 'learners':
            return User.objects.filter(profile__role='learner')
        elif self.target == 'premium':
            return User.objects.filter(profile__is_premium=True)
        return User.objects.none()


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200, blank=True, null=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content[:30]}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save()