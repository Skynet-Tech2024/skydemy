from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField
import json
from django.core.validators import MinValueValidator, MaxValueValidator

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('learner', 'Learner'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    )
    
    VERIFICATION_STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
    )
    
    LEVEL_CHOICES = (
        ('primary', 'Primary School'),
        ('secondary', 'Secondary School'),
        ('university', 'University / Higher Institution'),
        ('', 'Not set'),  # Empty string as default
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='learner')
    
    # --- Profile fields ---
    bio = models.TextField(blank=True)
    avatar = CloudinaryField('avatar', blank=True, null=True)
    
    # --- Level (now required) ---
    level = models.CharField(
        max_length=10, 
        choices=LEVEL_CHOICES, 
        default='', 
        help_text="Your education level"
    )
    
    # --- Date of Birth (new) ---
    date_of_birth = models.DateField(
        null=True, 
        blank=True, 
        help_text="Your date of birth"
    )
    
    # --- Address (new) ---
    address = models.TextField(
        blank=True, 
        help_text="Your physical address"
    )
    
    # --- WhatsApp number removed ---
    # whatsapp_number removed per user request
    
    # --- Verification ---
    verification_status = models.CharField(
        max_length=10, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending'
    )
    verification_notes = models.TextField(blank=True)
    
    # --- Premium ---
    is_premium = models.BooleanField(default=False)
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    
    # --- Suspension ---
    is_suspended = models.BooleanField(default=False)
    
    # --- Stats ---
    total_lessons_completed = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    
    # --- Timestamps ---
    joined_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def update_rating(self):
        """Calculate rating based on engagement and completed lessons"""
        base_rating = min(self.total_lessons_completed / 10, 5)
        self.rating = round(base_rating, 1)
        self.save(update_fields=['rating'])
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('follower', 'following')
    
    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'lesson')
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    subject = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.subject[:30]}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('system', 'System Notification'),
        ('message', 'New Message'),
        ('exam_result', 'Exam Result'),
        ('certificate_earned', 'Certificate Earned'),
        ('lesson_approved', 'Lesson Approved'),
        ('lesson_rejected', 'Lesson Rejected'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ProgressHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress_history')
    total_lessons_completed = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.recorded_at.date()}"

class WhatsAppAnnouncement(models.Model):
    """For sending announcements via WhatsApp (placeholder)"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    target_audience = models.CharField(max_length=20, choices=(
        ('all', 'All Users'),
        ('students', 'Students Only'),
        ('teachers', 'Teachers Only'),
        ('premium', 'Premium Users'),
    ))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

# ===== Signal to create UserProfile automatically =====
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()