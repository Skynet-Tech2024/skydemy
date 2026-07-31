from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0009_wishlist'),
        ('courses', '0001_initial'),  # 👈 point to the correct migration
    ]

    operations = [
        # No operations needed – this migration just fixes the dependency
    ]