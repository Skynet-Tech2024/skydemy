from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ProgressHistory
from courses.models import Progress

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