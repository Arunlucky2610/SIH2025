from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import Lesson
import os
import json

class Command(BaseCommand):
    help = 'Bulk upload lessons from a directory'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, help='Directory containing lesson files')
        parser.add_argument('--user', type=str, help='Username of the creator', default='admin')

    def handle(self, *args, **options):
        directory = options['directory']
        username = options['user']
        
        try:
            creator = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'User "{username}" does not exist')
            )
            return

        if not os.path.exists(directory):
            self.stdout.write(
                self.style.ERROR(f'Directory "{directory}" does not exist')
            )
            return

        lessons_created = 0
        
        # Look for lesson files
        for filename in os.listdir(directory):
            if filename.endswith(('.mp4', '.pdf', '.txt', '.html')):
                # Extract lesson info from filename
                name_parts = filename.split('_')
                if len(name_parts) >= 3:
                    lesson_type = name_parts[0]
                    language = name_parts[1]
                    title = ' '.join(name_parts[2:]).replace('.mp4', '').replace('.pdf', '').replace('.txt', '').replace('.html', '')
                    
                    # Create lesson
                    lesson = Lesson.objects.create(
                        title=title,
                        description=f"Auto-uploaded lesson: {title}",
                        lesson_type=lesson_type if lesson_type in ['basic', 'computer', 'internet', 'mobile', 'safety'] else 'basic',
                        language=language if language in ['en', 'hi', 'pa'] else 'en',
                        created_by=creator,
                        order=lessons_created + 1
                    )
                    
                    # Copy file to media directory if needed
                    # For now, just reference the filename
                    if filename.endswith('.mp4'):
                        lesson.video_url = f"file://{os.path.join(directory, filename)}"
                    else:
                        # For other files, you'd copy them to MEDIA_ROOT/lessons/
                        pass
                    
                    lesson.save()
                    lessons_created += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Created lesson: {lesson.title}')
                    )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {lessons_created} lessons')
        )