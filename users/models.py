from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from cloudinary.models import CloudinaryField
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
        ('', 'Not set'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='learner')

    bio = models.TextField(blank=True, default='')
    avatar = CloudinaryField('avatar', blank=True, null=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True, default='')

    verification_status = models.CharField(max_length=10, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    verification_notes = models.TextField(blank=True)

    is_premium = models.BooleanField(default=False)
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    is_suspended = models.BooleanField(default=False)

    total_lessons_completed = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)])

    joined_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def update_rating(self):
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
    subject = models.CharField(max_length=200, default='')
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
    title = models.CharField(max_length=200, default='')
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, default='')
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
    ), default='all')
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