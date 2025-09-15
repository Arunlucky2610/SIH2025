from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import UserProfile
from learning.teacher_communication_models import TeacherAssignment, TeacherProfile
from learning.models import Lesson

class Command(BaseCommand):
    help = 'Create sample teacher communication data'

    def handle(self, *args, **options):
        self.stdout.write("Creating sample teacher communication data...")
        
        # Create teacher users if they don't exist
        teachers_data = [
            {
                'username': 'teacher_math',
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@school.edu',
                'subject': 'computer',
                'specialization': 'Computer Basics and Digital Literacy',
                'years_experience': 8,
                'bio': 'Experienced computer teacher specializing in basic digital literacy and computer fundamentals for beginners.',
                'is_class_teacher': True
            },
            {
                'username': 'teacher_science',
                'first_name': 'Michael',
                'last_name': 'Chen',
                'email': 'michael.chen@school.edu',
                'subject': 'internet',
                'specialization': 'Internet Safety and Online Skills',
                'years_experience': 6,
                'bio': 'Digital safety expert helping students navigate the internet safely and effectively.',
                'is_class_teacher': False
            },
            {
                'username': 'teacher_digital',
                'first_name': 'Priya',
                'last_name': 'Sharma',
                'email': 'priya.sharma@school.edu',
                'subject': 'basic',
                'specialization': 'Basic Digital Literacy',
                'years_experience': 10,
                'bio': 'Passionate about teaching fundamental digital skills to rural communities and beginners.',
                'is_class_teacher': False
            },
            {
                'username': 'teacher_mobile',
                'first_name': 'David',
                'last_name': 'Wilson',
                'email': 'david.wilson@school.edu',
                'subject': 'mobile',
                'specialization': 'Mobile Technology and Apps',
                'years_experience': 4,
                'bio': 'Mobile technology specialist helping students learn smartphone and tablet usage effectively.',
                'is_class_teacher': False
            }
        ]
        
        created_teachers = 0
        created_profiles = 0
        created_assignments = 0
        
        for teacher_data in teachers_data:
            # Create or get teacher user
            teacher_user, created = User.objects.get_or_create(
                username=teacher_data['username'],
                defaults={
                    'first_name': teacher_data['first_name'],
                    'last_name': teacher_data['last_name'],
                    'email': teacher_data['email'],
                    'is_active': True
                }
            )
            
            if created:
                teacher_user.set_password('teacher123')
                teacher_user.save()
                created_teachers += 1
                self.stdout.write(f"✓ Created teacher user: {teacher_user.username}")
            
            # Create or get teacher profile
            teacher_profile, created = UserProfile.objects.get_or_create(
                user=teacher_user,
                defaults={'role': 'teacher'}
            )
            
            if created:
                self.stdout.write(f"✓ Created teacher profile for: {teacher_user.username}")
            
            # Create or get teacher extended profile
            extended_profile, created = TeacherProfile.objects.get_or_create(
                user=teacher_user,
                defaults={
                    'bio': teacher_data['bio'],
                    'specialization': teacher_data['specialization'],
                    'years_experience': teacher_data['years_experience'],
                    'allow_parent_messages': True,
                    'response_time_hours': 24,
                    'preferred_contact_time': 'Weekdays 9AM-5PM',
                    'office_location': 'Main Building, Room 101',
                    'office_hours': 'Monday-Friday 9:00AM-4:00PM'
                }
            )
            
            if created:
                created_profiles += 1
                self.stdout.write(f"✓ Created extended teacher profile for: {teacher_user.username}")
            
            # Create teacher assignment
            assignment, created = TeacherAssignment.objects.get_or_create(
                teacher=teacher_user,
                subject=teacher_data['subject'],
                defaults={
                    'class_name': f"Digital Learning Class A",
                    'is_class_teacher': teacher_data['is_class_teacher'],
                    'is_active': True
                }
            )
            
            if created:
                created_assignments += 1
                self.stdout.write(f"✓ Created teacher assignment: {teacher_user.username} -> {teacher_data['subject']}")
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Sample teacher communication data created successfully!\n"
                f"📊 Summary:\n"
                f"   - Teachers created: {created_teachers}\n"
                f"   - Teacher profiles created: {created_profiles}\n"
                f"   - Teacher assignments created: {created_assignments}\n\n"
                f"🔑 Teacher Login Credentials:\n"
                f"   - Username: teacher_math (Class Teacher)\n"
                f"   - Username: teacher_science\n"
                f"   - Username: teacher_digital\n"
                f"   - Username: teacher_mobile\n"
                f"   - Password: teacher123 (for all)\n\n"
                f"📱 Now parents can:\n"
                f"   1. Go to Teacher Communication section\n"
                f"   2. Select their child\n"
                f"   3. Choose a teacher to message\n"
                f"   4. Send messages and have conversations\n"
            )
        )