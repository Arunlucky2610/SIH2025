import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

from django.contrib.auth.models import User
from learning.models import UserProfile

print('Creating teacher account...')

# Create or get teacher user
user, created = User.objects.get_or_create(
    username='teacher1',
    defaults={
        'first_name': 'Teacher',
        'last_name': 'Test',
        'email': 'teacher@example.com'
    }
)

if created:
    user.set_password('teacher123')
    user.save()

# Create or get teacher profile
profile, profile_created = UserProfile.objects.get_or_create(
    user=user,
    defaults={
        'role': 'teacher',
        'language_preference': 'en'
    }
)

if created:
    print(f'Teacher account created: {user.username} (password: teacher123)')
else:
    print(f'Teacher account already exists: {user.username}')

# Check existing teachers
teachers = UserProfile.objects.filter(role='teacher')
print(f'\nAll teachers in database: {teachers.count()}')
for teacher in teachers:
    print(f'  - {teacher.user.username} ({teacher.user.first_name} {teacher.user.last_name})')