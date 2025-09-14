from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.models import UserProfile, Lesson, Quiz, ModuleProgress

class Command(BaseCommand):
    help = 'Populate database with sample data for rural education app'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create superuser if doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write('Created superuser: admin/admin123')
        
        # Create teacher user
        teacher_user, created = User.objects.get_or_create(
            username='teacher1',
            defaults={
                'first_name': 'Rajesh',
                'last_name': 'Kumar',
                'email': 'teacher@example.com'
            }
        )
        if created:
            teacher_user.set_password('teacher123')
            teacher_user.save()
        
        teacher_profile, _ = UserProfile.objects.get_or_create(
            user=teacher_user,
            defaults={
                'role': 'teacher',
                'language_preference': 'hi',
                'phone_number': '+91-9876543210'
            }
        )
        
        # Create student users
        students_data = [
            ('student1', 'Priya', 'Sharma', 'en'),
            ('student2', 'Amit', 'Singh', 'hi'),
            ('student3', 'Sunita', 'Kaur', 'pa'),
        ]
        
        student_users = []
        for username, first_name, last_name, lang in students_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': f'{username}@example.com'
                }
            )
            if created:
                user.set_password('student123')
                user.save()
            
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'student',
                    'language_preference': lang,
                    'phone_number': f'+91-987654321{len(student_users)}'
                }
            )
            student_users.append(user)
        
        # Create parent user
        parent_user, created = User.objects.get_or_create(
            username='parent1',
            defaults={
                'first_name': 'Ramesh',
                'last_name': 'Sharma',
                'email': 'parent@example.com'
            }
        )
        if created:
            parent_user.set_password('parent123')
            parent_user.save()
        
        parent_profile, _ = UserProfile.objects.get_or_create(
            user=parent_user,
            defaults={
                'role': 'parent',
                'language_preference': 'hi',
                'phone_number': '+91-9876543200'
            }
        )
        
        # Link first student to parent
        if student_users:
            first_student_profile = UserProfile.objects.get(user=student_users[0])
            first_student_profile.parent = parent_profile
            first_student_profile.save()
        
        # Create lessons
        lessons_data = [
            # Computer Basics
            ('Computer Basics - What is a Computer?', 'Learn about the basic components and functions of a computer', 'computer', 'en', 
             '''A computer is an electronic device that processes data and performs calculations. It consists of:
             
1. Hardware Components:
   - CPU (Central Processing Unit): The brain of the computer
   - Memory (RAM): Temporary storage for running programs
   - Storage (Hard Drive): Permanent storage for files and programs
   - Input devices: Keyboard, mouse, microphone
   - Output devices: Monitor, speakers, printer

2. Software:
   - Operating System: Windows, macOS, Linux
   - Applications: Programs like browsers, word processors
   
3. Basic Operations:
   - Input: Receiving data from user
   - Processing: Computing and manipulating data
   - Output: Displaying results to user
   - Storage: Saving data for future use
             '''),
            
            ('कंप्यूटर की मूल बातें', 'कंप्यूटर के बारे में जानें और इसके मुख्य भाग', 'computer', 'hi',
             '''कंप्यूटर एक इलेक्ट्रॉनिक उपकरण है जो डेटा को प्रोसेस करता है। इसके मुख्य भाग हैं:
             
1. हार्डवेयर:
   - CPU: कंप्यूटर का दिमाग
   - मेमोरी (RAM): अस्थायी भंडारण
   - स्टोरेज: स्थायी भंडारण
   - इनपुट डिवाइस: कीबोर्ड, माउस
   - आउटपुट डिवाइस: मॉनिटर, स्पीकर

2. सॉफ्टवेयर:
   - ऑपरेटिंग सिस्टम
   - एप्लिकेशन प्रोग्राम
             '''),
            
            # Internet Basics
            ('Internet Basics - Getting Online', 'Learn how to connect to and use the internet safely', 'internet', 'en',
             '''The Internet is a global network that connects computers worldwide. Here's what you need to know:
             
1. What is the Internet?
   - A network of networks connecting billions of devices
   - Allows sharing of information and communication
   - Accessible through various devices: computers, phones, tablets

2. How to Connect:
   - Wi-Fi: Wireless connection in homes, offices, public places
   - Mobile Data: Using cellular network on smartphones
   - Ethernet: Wired connection for computers

3. Essential Internet Services:
   - Web Browsing: Visiting websites using browsers like Chrome, Firefox
   - Email: Sending and receiving electronic messages
   - Social Media: Connecting with friends and family
   - Online Shopping: Buying products and services online

4. Internet Safety:
   - Use strong passwords
   - Don't share personal information with strangers
   - Be careful about what you download
   - Verify website authenticity before entering sensitive data
             '''),
            
            # Mobile Usage
            ('Mobile Phone Basics', 'Learn essential smartphone features and functions', 'mobile', 'en',
             '''Smartphones are powerful computers in your pocket. Here's how to use them effectively:
             
1. Basic Functions:
   - Making calls and sending SMS
   - Taking photos and videos
   - Installing and using apps
   - Connecting to Wi-Fi and mobile data

2. Essential Apps:
   - Phone: For making calls
   - Messages: For SMS and messaging
   - Camera: For photos and videos
   - Settings: To configure your phone
   - Browser: To access the internet

3. Safety Tips:
   - Set up screen lock (PIN, pattern, or fingerprint)
   - Keep your phone updated
   - Only download apps from official stores
   - Be careful about app permissions

4. Useful Features:
   - GPS for navigation
   - Calendar for scheduling
   - Calculator for quick math
   - Flashlight for emergencies
             '''),
            
            # Digital Safety  
            ('Digital Safety and Security', 'Learn how to stay safe online and protect your information', 'safety', 'en',
             '''Digital safety is crucial in today's connected world. Here are key practices:
             
1. Password Security:
   - Use strong, unique passwords for each account
   - Include letters, numbers, and special characters
   - Don't share passwords with others
   - Use password managers if possible

2. Personal Information Protection:
   - Don't share personal details (address, phone, ID numbers) online
   - Be cautious about what you post on social media
   - Check privacy settings on all accounts
   - Think before you share photos or videos

3. Safe Browsing:
   - Only visit trusted websites
   - Look for "https://" in the URL (secure connection)
   - Don't click on suspicious links or pop-ups
   - Verify website authenticity before entering sensitive data

4. Scam Awareness:
   - Be skeptical of "too good to be true" offers
   - Don't respond to suspicious emails or messages
   - Never send money to strangers online
   - Verify contacts through multiple channels

5. Device Security:
   - Keep software and apps updated
   - Use antivirus software on computers
   - Enable automatic screen locks
   - Don't connect to unsecured public Wi-Fi for sensitive activities
             '''),
        ]
        
        created_lessons = []
        for title, desc, lesson_type, lang, content in lessons_data:
            lesson, created = Lesson.objects.get_or_create(
                title=title,
                defaults={
                    'description': desc,
                    'lesson_type': lesson_type,
                    'language': lang,
                    'content': content,
                    'created_by': teacher_user,
                    'order': len(created_lessons) + 1
                }
            )
            created_lessons.append(lesson)
        
        # Create quizzes for lessons
        quiz_data = [
            # Computer Basics Quiz
            (created_lessons[0], "What does CPU stand for?", 
             "Computer Processing Unit", "Central Processing Unit", "Core Processing Unit", "Central Program Unit", "B"),
            (created_lessons[0], "Which of these is an input device?", 
             "Monitor", "Speaker", "Keyboard", "Printer", "C"),
            
            # Internet Basics Quiz
            (created_lessons[2], "What does WWW stand for?", 
             "World Wide Web", "World Web Wide", "Wide World Web", "Web World Wide", "A"),
            (created_lessons[2], "Which is safer for online banking?", 
             "HTTP websites", "HTTPS websites", "Any website", "Social media", "B"),
            
            # Mobile Basics Quiz
            (created_lessons[3], "What should you do to secure your phone?", 
             "Never update it", "Set up screen lock", "Share passwords", "Download any app", "B"),
            
            # Digital Safety Quiz
            (created_lessons[4], "What makes a strong password?", 
             "Your name only", "123456", "Letters, numbers, and symbols", "Your birthday", "C"),
            (created_lessons[4], "What should you do with suspicious emails?", 
             "Reply immediately", "Click all links", "Delete without opening", "Forward to friends", "C"),
        ]
        
        for lesson, question, opt_a, opt_b, opt_c, opt_d, correct in quiz_data:
            Quiz.objects.get_or_create(
                lesson=lesson,
                question=question,
                defaults={
                    'option_a': opt_a,
                    'option_b': opt_b,
                    'option_c': opt_c,
                    'option_d': opt_d,
                    'correct_answer': correct,
                    'order': 1
                }
            )
        
        # Create some progress for students
        for student in student_users:
            # Make first student complete first two lessons
            if student == student_users[0]:
                for lesson in created_lessons[:2]:
                    ModuleProgress.objects.get_or_create(
                        student=student,
                        lesson=lesson,
                        defaults={
                            'completed': True,
                            'score': 85
                        }
                    )
            # Make second student start first lesson
            elif student == student_users[1]:
                ModuleProgress.objects.get_or_create(
                    student=student,
                    lesson=created_lessons[0],
                    defaults={
                        'completed': False,
                        'score': None
                    }
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                'Successfully created sample data!\n\n'
                'Login credentials:\n'
                '- Admin: admin/admin123\n'
                '- Teacher: teacher1/teacher123\n'
                '- Students: student1/student123, student2/student123, student3/student123\n'
                '- Parent: parent1/parent123\n\n'
                f'Created {len(created_lessons)} lessons with quizzes'
            )
        )