import os
from django.core.management.base import BaseCommand
from django.core.files import File
from courses.models import Lesson

class Command(BaseCommand):
    help = 'Migrate all lesson PDFs from local media to Cloudinary'

    def handle(self, *args, **options):
        lessons = Lesson.objects.filter(pdf_file__isnull=False)
        for lesson in lessons:
            if lesson.pdf_file and not lesson.pdf_file.url.startswith('https://res.cloudinary.com'):
                local_path = lesson.pdf_file.path
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        lesson.pdf_file.save(
                            os.path.basename(local_path),
                            File(f),
                            save=True
                        )
                    self.stdout.write(f'✅ Migrated lesson {lesson.id}')
                else:
                    self.stdout.write(f'⚠️ File missing for lesson {lesson.id} – skipped')
            else:
                self.stdout.write(f'⏭️ Lesson {lesson.id} already on Cloudinary – skipped')
