from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from .models import Lesson, Exam, EarningsCycle, TeacherWallet
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=Lesson)
def update_earnings_on_lesson_approval(sender, instance, **kwargs):
    """When a lesson is approved, update the teacher's earnings cycle."""
    print(f"🔍 Lesson signal fired for lesson {instance.id}, status: {instance.status}, teacher: {instance.teacher}")
    
    # Only proceed if the lesson status is approved and it was just changed
    if instance.status == 'approved':
        print("✅ Lesson is approved, proceeding...")
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
            print(f"✅ Created new cycle {cycle.id} for teacher {instance.teacher.username}")

        # Count approved lessons for this teacher (only if not already counted)
        # We'll increment if this lesson wasn't previously counted
        if not getattr(instance, '_earnings_processed', False):
            print(f"✅ Incrementing lessons for cycle {cycle.id}, before: {cycle.approved_lessons}")
            cycle.approved_lessons += 1
            cycle.save()
            # Mark this lesson as processed to avoid double counting
            instance._earnings_processed = True
            print(f"✅ Lessons after increment: {cycle.approved_lessons}")

            # Check if cycle is complete
            if cycle.approved_lessons >= 5 and cycle.approved_exams >= 3:
                cycle.status = 'eligible'
                cycle.completed_at = None  # Will be set when claimed
                cycle.save()
                print(f"✅ Cycle {cycle.id} is now eligible!")
                
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
                print(f"✅ Wallet updated: available_balance = {wallet.available_balance}")
        else:
            print("ℹ️ Lesson already processed, skipping increment")
    else:
        print(f"ℹ️ Lesson status is {instance.status}, skipping")


@receiver(post_save, sender=Exam)
def update_earnings_on_exam_approval(sender, instance, **kwargs):
    """When an exam is approved, update the teacher's earnings cycle."""
    print(f"🔍 Exam signal fired for exam {instance.id}, status: {instance.status}, teacher: {instance.teacher}")
    
    # Only proceed if the exam status is approved and it has a teacher
    if instance.status == 'approved' and instance.teacher:
        print("✅ Exam is approved, proceeding...")
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
            print(f"✅ Created new cycle {cycle.id} for teacher {instance.teacher.username}")

        # Increment approved exams
        if not getattr(instance, '_earnings_processed', False):
            print(f"✅ Incrementing exams for cycle {cycle.id}, before: {cycle.approved_exams}")
            cycle.approved_exams += 1
            cycle.save()
            instance._earnings_processed = True
            print(f"✅ Exams after increment: {cycle.approved_exams}")

            # Check if cycle is complete
            if cycle.approved_lessons >= 5 and cycle.approved_exams >= 3:
                cycle.status = 'eligible'
                cycle.completed_at = None
                cycle.save()
                print(f"✅ Cycle {cycle.id} is now eligible!")
                
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
                print(f"✅ Wallet updated: available_balance = {wallet.available_balance}")
        else:
            print("ℹ️ Exam already processed, skipping increment")
    else:
        print(f"ℹ️ Exam status is {instance.status} or no teacher, skipping")


@receiver(post_delete, sender=Lesson)
def update_earnings_on_lesson_delete(sender, instance, **kwargs):
    """When a lesson is deleted, update the teacher's earnings cycle."""
    print(f"🔍 DELETE signal fired for lesson {instance.id}, status: {instance.status}, teacher: {instance.teacher}")
    
    if instance.status == 'approved' and instance.teacher:
        print("✅ Lesson was approved, proceeding with deletion...")
        # Get the current active cycle for this teacher
        cycle = EarningsCycle.objects.filter(
            teacher=instance.teacher,
            status__in=['pending', 'eligible']
        ).first()
        
        if cycle:
            print(f"✅ Found cycle {cycle.id}, approved_lessons before: {cycle.approved_lessons}")
            # Decrement the approved lessons count
            cycle.approved_lessons = max(0, cycle.approved_lessons - 1)
            print(f"✅ approved_lessons after decrement: {cycle.approved_lessons}")
            
            # If the cycle was eligible and now incomplete, revert it
            if cycle.status == 'eligible' and (cycle.approved_lessons < 5 or cycle.approved_exams < 3):
                cycle.status = 'pending'
                print(f"✅ Cycle reverted to pending (incomplete)")
                
                # Deduct the reward from the wallet
                wallet = TeacherWallet.objects.filter(teacher=instance.teacher).first()
                if wallet:
                    wallet.available_balance = max(0, wallet.available_balance - 5000)
                    wallet.total_earned = max(0, wallet.total_earned - 5000)
                    wallet.save()
                    print(f"✅ Wallet updated: available_balance = {wallet.available_balance}")
                else:
                    print("❌ No wallet found to deduct from")
            else:
                print(f"✅ Cycle status remains {cycle.status}")
            
            cycle.save()
            print(f"✅ Cycle saved with lessons: {cycle.approved_lessons}, exams: {cycle.approved_exams}")
        else:
            print("❌ No active cycle found for this teacher")
    else:
        print(f"❌ Lesson not approved or teacher missing. status: {instance.status}, teacher: {instance.teacher}")


@receiver(post_delete, sender=Exam)
def update_earnings_on_exam_delete(sender, instance, **kwargs):
    """When an exam is deleted, update the teacher's earnings cycle."""
    print(f"🔍 DELETE signal fired for exam {instance.id}, status: {instance.status}, teacher: {instance.teacher}")
    
    if instance.status == 'approved' and instance.teacher:
        print("✅ Exam was approved, proceeding with deletion...")
        # Get the current active cycle for this teacher
        cycle = EarningsCycle.objects.filter(
            teacher=instance.teacher,
            status__in=['pending', 'eligible']
        ).first()
        
        if cycle:
            print(f"✅ Found cycle {cycle.id}, approved_exams before: {cycle.approved_exams}")
            # Decrement the approved exams count
            cycle.approved_exams = max(0, cycle.approved_exams - 1)
            print(f"✅ approved_exams after decrement: {cycle.approved_exams}")
            
            # If the cycle was eligible and now incomplete, revert it
            if cycle.status == 'eligible' and (cycle.approved_lessons < 5 or cycle.approved_exams < 3):
                cycle.status = 'pending'
                print(f"✅ Cycle reverted to pending (incomplete)")
                
                # Deduct the reward from the wallet
                wallet = TeacherWallet.objects.filter(teacher=instance.teacher).first()
                if wallet:
                    wallet.available_balance = max(0, wallet.available_balance - 5000)
                    wallet.total_earned = max(0, wallet.total_earned - 5000)
                    wallet.save()
                    print(f"✅ Wallet updated: available_balance = {wallet.available_balance}")
                else:
                    print("❌ No wallet found to deduct from")
            else:
                print(f"✅ Cycle status remains {cycle.status}")
            
            cycle.save()
            print(f"✅ Cycle saved with lessons: {cycle.approved_lessons}, exams: {cycle.approved_exams}")
        else:
            print("❌ No active cycle found for this teacher")
    else:
        print(f"❌ Exam not approved or teacher missing. status: {instance.status}, teacher: {instance.teacher}")