from django.db import migrations

def add_departments(apps, schema_editor):
    Department = apps.get_model('courses', 'Department')
    departments = [
        {'name': 'General Education', 'code': 'GEN'},
        {'name': 'Commercial Education', 'code': 'COM'},
        {'name': 'Industrial Education', 'code': 'IND'},
    ]
    for dept in departments:
        Department.objects.get_or_create(name=dept['name'], defaults={'code': dept['code']})

def remove_departments(apps, schema_editor):
    Department = apps.get_model('courses', 'Department')
    Department.objects.filter(name__in=['General Education', 'Commercial Education', 'Industrial Education']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_add_department_to_subject'),  # Use the last migration name
    ]

    operations = [
        migrations.RunPython(add_departments, remove_departments),
    ]