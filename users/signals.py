from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, ProgressHistory
from courses.models import Progress

# Signal to create UserProfile when a new User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            role='learner',
            verification_status='pending'  # Fixed field name
        )
        print(f"✅ UserProfile created for {instance.username}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists (if somehow missing)
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(
            user=instance,
            role='learner',
            verification_status='pending'
        )

@receiver(post_save, sender=Progress)
def record_progress_history(sender, instance, created, **kwargs):
    # Only record when progress is updated and completed is True
    if instance.completed and instance.progress_percentage == 100:
        # Check if we already recorded history for today (avoid duplicates)
        today = timezone.now().date()
        existing = ProgressHistory.objects.filter(
            user=instance.user,
            recorded_at__date=today
        ).first()
        if not existing:
            profile = instance.user.profile
            ProgressHistory.objects.create(
                user=instance.user,
                total_lessons_completed=profile.total_lessons_completed,
                rating=profile.rating
            )