from django.db import migrations

def populate_subject_code(apps, schema_editor):
    Subject = apps.get_model('courses', 'Subject')
    for subject in Subject.objects.filter(code__isnull=True):
        # Set a temporary unique value
        subject.code = f"TEMP-{subject.id}"
        subject.save()

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0019_alter_exam_updated_at_alter_subject_code'),
    ]

    operations = [
        migrations.RunPython(populate_subject_code),
    ]