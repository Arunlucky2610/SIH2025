from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import Module, ModuleProgress, UserProfile
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Create sample data for analytics demonstration'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create subjects and modules
        subjects = ['Mathematics', 'Science', 'English', 'Social Studies', 'Art']
        
        modules_created = 0
        for subject in subjects:
            for i in range(5):  # 5 modules per subject
                module, created = Module.objects.get_or_create(
                    title=f"{subject} - Lesson {i+1}",
                    defaults={
                        'subject': subject,
                        'content': f'Sample content for {subject} lesson {i+1}',
                        'order': i+1,
                        'created_at': datetime.now() - timedelta(days=random.randint(1, 30))
                    }
                )
                if created:
                    modules_created += 1
        
        self.stdout.write(f'Created {modules_created} new modules')
        
        # Find or create parent and student users
        try:
            parent_user = User.objects.get(username='nandini1')
        except User.DoesNotExist:
            self.stdout.write('Parent user nandini1 not found. Please ensure you are logged in as a parent.')
            return
        
        # Create sample children if they don't exist
        children_created = 0
        for i in range(2):  # Create 2 children
            child_username = f'child{i+1}_{parent_user.username}'
            child_user, created = User.objects.get_or_create(
                username=child_username,
                defaults={
                    'first_name': f'Child {i+1}',
                    'last_name': parent_user.last_name or 'Test',
                    'email': f'{child_username}@example.com'
                }
            )
            
            if created:
                children_created += 1
                # Create UserProfile for child
                child_profile, _ = UserProfile.objects.get_or_create(
                    user=child_user,
                    defaults={
                        'role': 'student',
                        'grade': 5,
                        'parent': parent_user.userprofile
                    }
                )
                
                # Create progress for some modules
                modules = list(Module.objects.all())
                for module in random.sample(modules, random.randint(5, 15)):
                    progress, created = ModuleProgress.objects.get_or_create(
                        student=child_user,
                        module=module,
                        defaults={
                            'completed': random.choice([True, False, False]),  # 33% chance of completion
                            'score': random.randint(60, 95) if random.random() > 0.5 else None,
                            'time_spent': timedelta(minutes=random.randint(15, 120)),
                            'started_at': datetime.now() - timedelta(days=random.randint(1, 15))
                        }
                    )
        
        self.stdout.write(f'Created {children_created} new children')
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('You can now view the analytics with sample data.')