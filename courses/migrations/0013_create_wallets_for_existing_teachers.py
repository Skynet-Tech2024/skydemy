from django.db import migrations
from django.contrib.auth import get_user_model

User = get_user_model()


def create_wallets_for_existing_teachers(apps, schema_editor):
    # Get the models
    TeacherWallet = apps.get_model('courses', 'TeacherWallet')
    User = apps.get_model('auth', 'User')
    
    # Try to get UserProfile model if it exists
    UserProfile = None
    try:
        UserProfile = apps.get_model('users', 'UserProfile')
    except LookupError:
        pass
    
    # Get all teachers
    if UserProfile:
        # Get users with teacher role
        teacher_ids = UserProfile.objects.filter(role='teacher').values_list('user_id', flat=True)
        teachers = User.objects.filter(id__in=teacher_ids)
    else:
        # Fallback: get users who have uploaded lessons
        Lesson = apps.get_model('courses', 'Lesson')
        teacher_ids = Lesson.objects.values_list('teacher_id', flat=True).distinct()
        teachers = User.objects.filter(id__in=teacher_ids)
    
    # Create wallets for each teacher
    count = 0
    for teacher in teachers:
        wallet, created = TeacherWallet.objects.get_or_create(
            teacher=teacher,
            defaults={
                'available_balance': 0,
                'total_earned': 0,
                'total_withdrawn': 0
            }
        )
        if created:
            count += 1
    
    if count > 0:
        print(f"Created {count} teacher wallet(s).")


def reverse_migration(apps, schema_editor):
    # Optional: Delete all wallets (not recommended for production)
    TeacherWallet = apps.get_model('courses', 'TeacherWallet')
    TeacherWallet.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0012_earningscycle_teacherwallet_withdrawalrequest'),
    ]

    operations = [
        migrations.RunPython(create_wallets_for_existing_teachers, reverse_migration),
    ]