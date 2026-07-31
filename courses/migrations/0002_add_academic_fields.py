from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='cycle',
            field=models.CharField(blank=True, choices=[('first', 'First Cycle'), ('second', 'Second Cycle')], max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='lesson',
            name='class_level',
            field=models.CharField(blank=True, choices=[('form3', 'Form 3'), ('form4', 'Form 4'), ('form5', 'Form 5'), ('lower_sixth', 'Lower Sixth'), ('upper_sixth', 'Upper Sixth')], max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='lesson',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='courses.department'),
        ),
    ]