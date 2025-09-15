from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import UserProfile

class Command(BaseCommand):
    help = 'Create test users for different roles'

    def handle(self, *args, **options):
        # Create test parent user
        parent_username = 'testparent'
        parent_email = 'parent@test.com'
        parent_password = 'testpass123'
        
        # Check if parent user already exists
        if User.objects.filter(username=parent_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Parent user "{parent_username}" already exists')
            )
            parent_user = User.objects.get(username=parent_username)
        else:
            # Create parent user
            parent_user = User.objects.create_user(
                username=parent_username,
                email=parent_email,
                password=parent_password,
                first_name='Test',
                last_name='Parent'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created parent user: {parent_username}')
            )
        
        # Create or get parent profile
        parent_profile, created = UserProfile.objects.get_or_create(
            user=parent_user,
            defaults={
                'role': 'parent',
                'phone_number': '+1234567890',
                'language_preference': 'en'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created parent profile for: {parent_username}')
            )
        else:
            # Update role if it exists but isn't parent
            if parent_profile.role != 'parent':
                parent_profile.role = 'parent'
                parent_profile.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Updated role to parent for: {parent_username}')
                )
        
        # Create test student user as child
        student_username = 'teststudent'
        student_email = 'student@test.com'
        student_password = 'testpass123'
        
        if User.objects.filter(username=student_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Student user "{student_username}" already exists')
            )
            student_user = User.objects.get(username=student_username)
        else:
            student_user = User.objects.create_user(
                username=student_username,
                email=student_email,
                password=student_password,
                first_name='Test',
                last_name='Student'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created student user: {student_username}')
            )
        
        # Create or get student profile
        student_profile, created = UserProfile.objects.get_or_create(
            user=student_user,
            defaults={
                'role': 'student',
                'parent': parent_profile,
                'language_preference': 'en'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created student profile for: {student_username}')
            )
        else:
            # Link to parent if not already linked
            if student_profile.parent != parent_profile:
                student_profile.parent = parent_profile
                student_profile.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Linked student to parent: {student_username} -> {parent_username}')
                )
        
        self.stdout.write(
            self.style.SUCCESS('\n=== Test Users Created ===')
        )
        self.stdout.write(f'Parent Login:')
        self.stdout.write(f'  Username: {parent_username}')
        self.stdout.write(f'  Password: {parent_password}')
        self.stdout.write(f'  URL: http://127.0.0.1:8000/login/')
        self.stdout.write(f'\nStudent Login:')
        self.stdout.write(f'  Username: {student_username}')
        self.stdout.write(f'  Password: {student_password}')
        self.stdout.write(f'\nAfter logging in as parent, visit:')
        self.stdout.write(f'  http://127.0.0.1:8000/parents/parent-dashboard-test/')