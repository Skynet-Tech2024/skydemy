from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Lesson, Exam, EarningsCycle, TeacherWallet
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=Lesson)
def update_earnings_on_lesson_approval(sender, instance, **kwargs):
    """When a lesson is approved, update the teacher's earnings cycle."""
    # Only proceed if the lesson status is approved and it was just changed
    if instance.status == 'approved':
        # Get or create an open earnings cycle for this teacher
        cycle = EarningsCycle.objects.filter(
            teacher=instance.teacher,
            status__in=['pending', 'eligible']
        ).first()

        if not cycle:
            # Create a new cycle if none exists
            cycle = EarningsCycle.objects.create(
                teacher=instance.teacher
            )

        # Count approved lessons for this teacher (only if not already counted)
        # We'll increment if this lesson wasn't previously counted
        if not getattr(instance, '_earnings_processed', False):
            cycle.approved_lessons += 1
            cycle.save()
            # Mark this lesson as processed to avoid double counting
            instance._earnings_processed = True

            # Check if cycle is complete
            if cycle.approved_lessons >= 5 and cycle.approved_exams >= 3:
                cycle.status = 'eligible'
                cycle.completed_at = None  # Will be set when claimed
                cycle.save()
                
                # Create or update teacher wallet
                wallet, created = TeacherWallet.objects.get_or_create(
                    teacher=instance.teacher,
                    defaults={
                        'available_balance': 0,
                        'total_earned': 0,
                        'total_withdrawn': 0
                    }
                )
                # Add to available balance
                wallet.available_balance += 5000
                wallet.total_earned += 5000
                wallet.save()


@receiver(post_save, sender=Exam)
def update_earnings_on_exam_approval(sender, instance, **kwargs):
    """When an exam is approved, update the teacher's earnings cycle."""
    # Only proceed if the exam status is approved and it has a teacher
    if instance.status == 'approved' and instance.teacher:
        # Get or create an open earnings cycle for this teacher
        cycle = EarningsCycle.objects.filter(
            teacher=instance.teacher,
            status__in=['pending', 'eligible']
        ).first()

        if not cycle:
            # Create a new cycle if none exists
            cycle = EarningsCycle.objects.create(
                teacher=instance.teacher
            )

        # Increment approved exams
        if not getattr(instance, '_earnings_processed', False):
            cycle.approved_exams += 1
            cycle.save()
            instance._earnings_processed = True

            # Check if cycle is complete
            if cycle.approved_lessons >= 5 and cycle.approved_exams >= 3:
                cycle.status = 'eligible'
                cycle.completed_at = None
                cycle.save()
                
                # Create or update teacher wallet
                wallet, created = TeacherWallet.objects.get_or_create(
                    teacher=instance.teacher,
                    defaults={
                        'available_balance': 0,
                        'total_earned': 0,
                        'total_withdrawn': 0
                    }
                )
                # Add to available balance
                wallet.available_balance += 5000
                wallet.total_earned += 5000
                wallet.save()