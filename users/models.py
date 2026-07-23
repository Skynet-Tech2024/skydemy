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
    
    bio = models.TextField(blank=True, default='')                     # <-- default added
    avatar = CloudinaryField('avatar', blank=True, null=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='')
    date_of_birth = models.DateField(null=True, blank=True)            # nullable, no default needed
    address = models.TextField(blank=True, default='')                 # <-- default added
    
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

# ... (rest of the file: Follow, Wishlist, Message, Notification, ProgressHistory, WhatsAppAnnouncement remain unchanged)