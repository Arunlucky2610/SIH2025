from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta
import json
import os

from .models import UserProfile, Lesson, ModuleProgress, Quiz, QuizAttempt, LessonDownload, LoginSession, Student, Parent, Teacher
from .analytics import (
    get_progress_chart_data, get_subject_performance_data, get_learning_calendar_data,
    get_current_streak, update_all_analytics_for_student
)
from .notifications import NotificationService
from .mongodb_utils import create_user_in_mongodb, get_user_by_username, update_user_login_session

def home(request):
    """Landing page - redirect based on user role"""
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            if profile.role == 'student':
                return redirect('student_dashboard')
            elif profile.role == 'teacher':
                return redirect('teacher_dashboard')
            elif profile.role == 'parent':
                return redirect('parent_dashboard')
        except UserProfile.DoesNotExist:
            # Create profile if doesn't exist
            UserProfile.objects.create(user=request.user, role='student')
            return redirect('student_dashboard')
    
    return render(request, 'learning/landing.html')

def user_login(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            
            # Create login session record
            def get_client_ip(request):
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')
                return ip
            
            LoginSession.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key
            )
            
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'learning/login.html')

def user_signup(request):
    """Enhanced user signup view with MongoDB integration and role-specific collections"""
    print(f"=== SIGNUP DEBUG: Method = {request.method} ===")
    
    if request.method == 'POST':
        print(f"POST data received: {dict(request.POST)}")
        role = request.POST.get('role', '').strip()
        print(f"Selected role: '{role}'")
        
        # Get form data based on role
        if role == 'student':
            print("Processing student signup...")
            username = request.POST.get('student_username', '').strip()
            first_name = request.POST.get('student_first_name', '').strip()
            last_name = request.POST.get('student_last_name', '').strip()
            school_type = request.POST.get('student_school_type', '').strip()
            father_mother_name = request.POST.get('student_parent_name', '').strip()
            parent_phone = request.POST.get('student_parent_phone', '').strip()
            class_level = request.POST.get('student_class_level', '').strip()
            date_of_birth = request.POST.get('student_date_of_birth', '').strip()
            school_name = request.POST.get('student_school_name', '').strip()
            
            print(f"Student data: username={username}, first_name={first_name}, last_name={last_name}")
            print(f"Student extra: school_type={school_type}, class_level={class_level}")
            
        elif role == 'parent':
            username = request.POST.get('parent_username', '').strip()
            name = request.POST.get('parent_full_name', '').strip()
            mobile = request.POST.get('parent_mobile_number', '').strip()
            children_name = request.POST.get('parent_children_name', '').strip()
            gender = request.POST.get('parent_gender', '').strip()
            email = request.POST.get('parent_email', '').strip()
            password = request.POST.get('parent_password', '').strip()
            
        elif role == 'teacher':
            username = request.POST.get('teacher_username', '').strip()
            name = request.POST.get('teacher_name', '').strip()
            mobile = request.POST.get('teacher_mobile', '').strip()
            email = request.POST.get('teacher_email', '').strip()
            password = request.POST.get('teacher_password', '').strip()
            teaching_class = request.POST.get('teacher_teaching_class', '').strip()
            school_name = request.POST.get('teacher_school_name', '').strip()
            school_type = request.POST.get('teacher_school_type', '').strip()
        
        # Validation
        errors = []
        print(f"Starting validation for role: {role}")
        
        # Validate role
        if not role or role not in ['student', 'teacher', 'parent']:
            errors.append('Please select a valid role')
            print(f"Invalid role error: {role}")
            return render(request, 'learning/signup.html', {'errors': errors})
        
        # Validate username (check both Django and MongoDB)
        if not username:
            errors.append('Username is required')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters long')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already exists')
        else:
            # Check MongoDB collections
            from .mongodb_utils import check_username_exists_in_collections
            if check_username_exists_in_collections(username):
                errors.append('Username already exists')
            
        # Role-specific validation
        if role == 'student':
            if not first_name:
                errors.append('First name is required')
            if not last_name:
                errors.append('Last name is required')
            if not school_type:
                errors.append('School type is required')
            if not father_mother_name:
                errors.append('Father/Mother name is required')
            if not parent_phone:
                errors.append('Parent phone number is required')
            if not class_level:
                errors.append('Class is required')
            if not date_of_birth:
                errors.append('Date of birth is required')
            if not school_name:
                errors.append('School name is required')
                
        elif role == 'parent':
            if not name:
                errors.append('Parent name is required')
            if not mobile:
                errors.append('Mobile number is required')
            if not children_name:
                errors.append('Children name is required')
            if not gender:
                errors.append('Gender is required')
            if not email:
                errors.append('Email is required')
            elif '@' not in email or '.' not in email.split('@')[-1]:
                errors.append('Please enter a valid email address')
            elif User.objects.filter(email=email).exists():
                errors.append('Email already exists')
            else:
                # Check MongoDB collections
                from .mongodb_utils import check_email_exists_in_collections
                if check_email_exists_in_collections(email):
                    errors.append('Email already exists')
            if not password:
                errors.append('Password is required')
            elif len(password) < 6:
                errors.append('Password must be at least 6 characters long')
                
        elif role == 'teacher':
            if not name:
                errors.append('Teacher name is required')
            if not mobile:
                errors.append('Mobile number is required')
            if not email:
                errors.append('Email is required')
            elif '@' not in email or '.' not in email.split('@')[-1]:
                errors.append('Please enter a valid email address')
            elif User.objects.filter(email=email).exists():
                errors.append('Email already exists')
            else:
                # Check MongoDB collections
                from .mongodb_utils import check_email_exists_in_collections
                if check_email_exists_in_collections(email):
                    errors.append('Email already exists')
            if not password:
                errors.append('Password is required')
            elif len(password) < 6:
                errors.append('Password must be at least 6 characters long')
            if not teaching_class:
                errors.append('Teaching class is required')
            if not school_name:
                errors.append('School name is required')
            if not school_type:
                errors.append('School type is required')
        
        # If there are validation errors, return to form with errors
        if errors:
            print(f"Validation errors found: {errors}")
            return render(request, 'learning/signup.html', {'errors': errors})
        
        print("Validation passed, proceeding to save data...")
        
        try:
            # Prepare data for MongoDB storage
            mongodb_data = {
                'username': username,
                'role': role
            }
            
            if role == 'student':
                mongodb_data.update({
                    'firstName': first_name,
                    'lastName': last_name,
                    'schoolType': school_type,
                    'fatherMotherName': father_mother_name,
                    'parentPhone': parent_phone,
                    'class': class_level,
                    'dateOfBirth': date_of_birth,
                    'schoolName': school_name,
                    'password': 'student123'  # Default password for students
                })
                collection_name = 'students'
                email = f"{username}@student.rural-learning.com"  # Generate email for students
                
            elif role == 'parent':
                mongodb_data.update({
                    'name': name,
                    'mobile': mobile,
                    'childrenName': children_name,
                    'gender': gender,
                    'email': email,
                    'password': password
                })
                collection_name = 'parents'
                
            elif role == 'teacher':
                mongodb_data.update({
                    'name': name,
                    'mobile': mobile,
                    'email': email,
                    'password': password,
                    'teachingClass': teaching_class,
                    'schoolName': school_name,
                    'schoolType': school_type
                })
                collection_name = 'teachers'
            
            # Save to MongoDB
            from .mongodb_utils import save_to_role_collection
            print(f"Saving to MongoDB collection: {collection_name}")
            print(f"MongoDB data: {mongodb_data}")
            
            mongodb_result = save_to_role_collection(collection_name, mongodb_data)
            print(f"MongoDB save result: {mongodb_result}")
            
            if not mongodb_result:
                errors.append('Failed to save data. Please try again.')
                print("MongoDB save failed!")
                return render(request, 'learning/signup.html', {'errors': errors})
            
            print("MongoDB save successful, creating Django user...")
            
            # Create Django User for authentication
            user = User.objects.create_user(
                username=username,
                email=email,
                password=mongodb_data['password']
            )
            print(f"Django user created: {user}")
            
            # Create UserProfile
            profile_data = {
                'user': user,
                'role': role,
                'language_preference': 'en'
            }
            
            if role == 'student':
                profile_data['grade'] = class_level
            elif role == 'teacher':
                profile_data['subject'] = teaching_class
            elif role == 'parent':
                profile_data['child_name'] = children_name
            
            print(f"Creating UserProfile with data: {profile_data}")
            
            UserProfile.objects.create(**profile_data)
            print("UserProfile created successfully!")
            
            # Log the user in automatically
            login(request, user)
            print(f"User logged in: {user.is_authenticated}")
            
            # Create login session record
            def get_client_ip(request):
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')
                return ip
            
            LoginSession.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key
            )
            
            # Success message
            role_display = {
                'student': 'Student',
                'teacher': 'Teacher', 
                'parent': 'Parent'
            }.get(role, 'User')
            
            messages.success(request, f'Welcome to Rural Learning Platform, {username}! Your {role_display} account has been created successfully.')
            
            print(f"About to redirect for role: {role}")
            
            # Redirect based on role
            if role == 'student':
                print("Redirecting to student_dashboard...")
                return redirect('student_dashboard')
            elif role == 'teacher':
                print("Redirecting to teacher_dashboard...")
                return redirect('teacher_dashboard')
            elif role == 'parent':
                print("Redirecting to parent_dashboard...")
                return redirect('parent_dashboard')
            else:
                print("Redirecting to home...")
                return redirect('home')
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            errors.append(f'An error occurred while creating your account: {str(e)}')
            print(f"Signup error: {str(e)}")  # For debugging
            print(f"Full traceback: {error_details}")  # For debugging
            return render(request, 'learning/signup.html', {'errors': errors})
    
    return render(request, 'learning/signup.html')

def user_logout(request):
    """User logout view"""
    if request.user.is_authenticated:
        # Mark current login session as ended
        try:
            current_session = LoginSession.objects.filter(
                user=request.user,
                session_key=request.session.session_key,
                is_active=True
            ).first()
            if current_session:
                current_session.logout_time = timezone.now()
                current_session.is_active = False
                current_session.save()
        except Exception as e:
            pass  # Don't let session tracking errors break logout
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def student_dashboard(request):
    """Student dashboard view"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'student':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get lessons based on language preference
    lessons = Lesson.objects.filter(
        Q(language=profile.language_preference) | Q(language='en'),
        is_active=True
    ).order_by('lesson_type', 'order')
    
    # Get user progress
    progress = ModuleProgress.objects.filter(student=request.user)
    progress_dict = {p.lesson_id: p for p in progress}
    
    # Calculate overall progress
    total_lessons = lessons.count()
    completed_lessons = progress.filter(completed=True).count()
    progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    # Get recent downloads
    recent_downloads = LessonDownload.objects.filter(
        student=request.user
    ).order_by('-downloaded_at')[:5]
    
    context = {
        'lessons': lessons,
        'progress_dict': progress_dict,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'progress_percentage': progress_percentage,
        'recent_downloads': recent_downloads,
        'profile': profile,
    }
    
    return render(request, 'learning/student_dashboard.html', context)

@login_required
def teacher_dashboard(request):
    """Teacher dashboard view"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'teacher' and not request.user.is_staff:
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get all students
    students = User.objects.filter(userprofile__role='student').select_related('userprofile')
    
    # Get lessons created by teacher
    lessons = Lesson.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Get student progress summary
    progress_summary = []
    for student in students:
        total_progress = ModuleProgress.objects.filter(student=student)
        completed_count = total_progress.filter(completed=True).count()
        total_count = total_progress.count()
        avg_score = total_progress.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0
        
        progress_summary.append({
            'student': student,
            'completed_lessons': completed_count,
            'total_lessons': total_count,
            'avg_score': round(avg_score, 1),
            'progress_percentage': (completed_count / total_count * 100) if total_count > 0 else 0
        })
    
    # Recent quiz attempts
    recent_attempts = QuizAttempt.objects.select_related('student', 'quiz__lesson').order_by('-attempted_at')[:10]
    
    context = {
        'students': students,
        'lessons': lessons,
        'progress_summary': progress_summary,
        'recent_attempts': recent_attempts,
        'profile': profile,
        'today': timezone.now().date(),
    }
    
    return render(request, 'learning/teacher_dashboard.html', context)

@login_required
def parent_dashboard(request):
    """Enhanced parent dashboard view with analytics"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'parent':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get children (students linked to this parent)
    children = UserProfile.objects.filter(parent=profile)
    
    children_progress = []
    for child_profile in children:
        child = child_profile.user
        
        # Update analytics for this child
        update_all_analytics_for_student(child)
        
        # Basic progress data
        progress = ModuleProgress.objects.filter(student=child)
        completed_count = progress.filter(completed=True).count()
        total_count = progress.count()
        avg_score = progress.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0
        
        # Recent activity
        recent_progress = progress.order_by('-started_at')[:5]
        
        # Enhanced analytics
        current_streak = get_current_streak(child)
        
        # Time spent this week
        from .models import WeeklyProgress
        from datetime import timedelta
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        try:
            weekly_progress = WeeklyProgress.objects.get(student=child, week_start=week_start)
            weekly_time = weekly_progress.total_time_spent.total_seconds() / 3600  # hours
            weekly_lessons = weekly_progress.lessons_completed
        except WeeklyProgress.DoesNotExist:
            weekly_time = 0
            weekly_lessons = 0
        
        # Get chart data for this child
        progress_chart_data = get_progress_chart_data(child, period='month')
        subject_performance_data = get_subject_performance_data(child)
        
        # Convert data to JSON-safe format
        import json
        progress_chart_json = {
            'labels': json.dumps(progress_chart_data.get('labels', [])),
            'lessons': json.dumps(progress_chart_data.get('lessons', [])),
            'scores': json.dumps(progress_chart_data.get('scores', [])),
            'time': json.dumps(progress_chart_data.get('time', []))
        }
        
        subject_performance_json = {
            'subjects': json.dumps(subject_performance_data.get('subjects', [])),
            'completion': json.dumps(subject_performance_data.get('completion', [])),
            'scores': json.dumps(subject_performance_data.get('scores', []))
        }
        
        # Calendar data for current month
        now = timezone.now()
        calendar_data = get_learning_calendar_data(child, now.year, now.month)
        
        children_progress.append({
            'child': child,
            'profile': child_profile,
            'completed_lessons': completed_count,
            'total_lessons': total_count,
            'avg_score': round(avg_score, 1),
            'progress_percentage': (completed_count / total_count * 100) if total_count > 0 else 0,
            'recent_progress': recent_progress,
            # Enhanced analytics
            'current_streak': current_streak,
            'weekly_time_hours': round(weekly_time, 1),
            'weekly_lessons': weekly_lessons,
            'progress_chart_data': progress_chart_json,
            'subject_performance_data': subject_performance_json,
            'calendar_data': calendar_data,
        })
    
    context = {
        'children_progress': children_progress,
        'profile': profile,
        'current_year': timezone.now().year,
        'current_month': timezone.now().month,
        # Summary statistics
        'children_count': len(children),
        'total_assignments': sum(child['total_lessons'] for child in children_progress),
        'completed_assignments': sum(child['completed_lessons'] for child in children_progress),
        'pending_assignments': sum(child['total_lessons'] - child['completed_lessons'] for child in children_progress),
        # Notification data
        'unread_notifications': NotificationService.get_unread_notifications(request.user)[:10],  # Latest 10
        'notification_count': NotificationService.get_unread_notifications(request.user).count(),
    }
    
    return render(request, 'learning/parent_dashboard_ultra.html', context)


@login_required
def parent_analytics(request):
    """Detailed analytics page for parents"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'parent':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get children (students linked to this parent)
    children = UserProfile.objects.filter(parent=profile)
    
    # Aggregate analytics data for all children
    total_lessons = 0
    completed_lessons = 0
    in_progress_lessons = 0
    pending_lessons = 0
    total_time_spent = 0
    
    # Subject-wise analytics
    subjects_data = {}
    detailed_children_data = []
    
    for child_profile in children:
        child = child_profile.user
        
        # Update analytics for this child
        update_all_analytics_for_student(child)
        
        # Progress data
        progress = ModuleProgress.objects.filter(student=child)
        completed_count = progress.filter(completed=True).count()
        total_count = progress.count()
        in_progress_count = progress.filter(completed=False, started_at__isnull=False).count()
        pending_count = total_count - completed_count - in_progress_count
        
        # Subject-wise progress
        from .models import Module
        modules_by_subject = Module.objects.values('subject').distinct()
        
        for subject_data in modules_by_subject:
            subject = subject_data['subject']
            if subject not in subjects_data:
                subjects_data[subject] = {
                    'total_lessons': 0,
                    'completed_lessons': 0,
                    'in_progress_lessons': 0,
                    'pending_lessons': 0,
                    'total_time_spent': 0,
                    'avg_score': 0,
                    'performance_trend': [],
                    'children_progress': []
                }
            
            # Get subject-specific progress for this child
            subject_modules = Module.objects.filter(subject=subject)
            subject_progress = progress.filter(module__in=subject_modules)
            
            subject_completed = subject_progress.filter(completed=True).count()
            subject_total = subject_progress.count()
            subject_in_progress = subject_progress.filter(completed=False, started_at__isnull=False).count()
            subject_pending = subject_total - subject_completed - subject_in_progress
            
            # Calculate time spent on this subject
            subject_time = 0
            for prog in subject_progress:
                if prog.time_spent:
                    subject_time += prog.time_spent.total_seconds() / 3600
            
            # Calculate average score for this subject
            completed_progress = subject_progress.filter(completed=True)
            if completed_progress.exists():
                avg_score = sum([p.score for p in completed_progress if p.score]) / completed_progress.count()
            else:
                avg_score = 0
            
            # Add to subject data
            subjects_data[subject]['total_lessons'] += subject_total
            subjects_data[subject]['completed_lessons'] += subject_completed
            subjects_data[subject]['in_progress_lessons'] += subject_in_progress
            subjects_data[subject]['pending_lessons'] += subject_pending
            subjects_data[subject]['total_time_spent'] += subject_time
            
            # Add child's progress for this subject
            completion_rate = (subject_completed / subject_total * 100) if subject_total > 0 else 0
            subjects_data[subject]['children_progress'].append({
                'child_name': f"{child.first_name} {child.last_name}",
                'completion_rate': round(completion_rate, 1),
                'completed': subject_completed,
                'total': subject_total,
                'time_spent': round(subject_time, 1),
                'avg_score': round(avg_score, 1)
            })
        
        # Time tracking
        from .models import WeeklyProgress
        from datetime import timedelta
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        try:
            weekly_progress = WeeklyProgress.objects.get(student=child, week_start=week_start)
            weekly_time = weekly_progress.total_time_spent.total_seconds() / 3600  # hours
        except WeeklyProgress.DoesNotExist:
            weekly_time = 0
        
        # Add to totals
        total_lessons += total_count
        completed_lessons += completed_count
        in_progress_lessons += in_progress_count
        pending_lessons += pending_count
        total_time_spent += weekly_time
        
        detailed_children_data.append({
            'child': child,
            'profile': child_profile,
            'completed_lessons': completed_count,
            'total_lessons': total_count,
            'in_progress_lessons': in_progress_count,
            'pending_lessons': pending_count,
            'weekly_time_hours': round(weekly_time, 1),
        })
    
    # Calculate subject averages and completion rates
    for subject, data in subjects_data.items():
        if data['total_lessons'] > 0:
            data['completion_rate'] = round((data['completed_lessons'] / data['total_lessons']) * 100, 1)
        else:
            data['completion_rate'] = 0
        
        data['total_time_spent'] = round(data['total_time_spent'], 1)
        
        # Calculate average performance for the subject
        if data['children_progress']:
            data['avg_performance'] = round(
                sum([child['avg_score'] for child in data['children_progress']]) / len(data['children_progress']), 1
            )
        else:
            data['avg_performance'] = 0
    
    # Format total time spent
    if total_time_spent < 1:
        time_display = f"{int(total_time_spent * 60)}m"
    else:
        time_display = f"{int(total_time_spent)}h {int((total_time_spent % 1) * 60)}m"
    
    # Calculate completion rate
    if total_lessons > 0:
        completion_rate = round((completed_lessons / total_lessons) * 100, 1)
    else:
        completion_rate = 0
    
    context = {
        'children_data': detailed_children_data,
        'subjects_data': subjects_data,
        'profile': profile,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'in_progress_lessons': in_progress_lessons,
        'pending_lessons': pending_lessons,
        'total_time_spent': time_display,
        'completion_rate': completion_rate,
        'children_count': len(children),
    }
    
    return render(request, 'learning/parent_analytics.html', context)


@login_required
def notifications_view(request):
    """View all notifications for parent"""
    if request.user.userprofile.role != 'parent':
        return redirect('dashboard')
    
    notifications = NotificationService.get_unread_notifications(request.user)
    
    # Mark as read if requested
    if request.method == 'POST' and request.POST.get('mark_all_read'):
        NotificationService.mark_all_as_read(request.user)
        messages.success(request, "All notifications marked as read!")
        return redirect('notifications')
    
    context = {
        'notifications': notifications,
        'notification_count': notifications.count(),
    }
    
    return render(request, 'learning/notifications.html', context)


@login_required
def notification_settings(request):
    """Manage notification settings"""
    if request.user.userprofile.role != 'parent':
        return redirect('dashboard')
    
    from .notification_models import NotificationSettings
    
    # Get or create settings
    settings, created = NotificationSettings.objects.get_or_create(parent=request.user)
    
    if request.method == 'POST':
        # Update settings
        settings.in_app_notifications = request.POST.get('in_app_notifications') == 'on'
        settings.email_notifications = request.POST.get('email_notifications') == 'on'
        settings.sms_notifications = request.POST.get('sms_notifications') == 'on'
        
        # Quiet hours
        quiet_start = request.POST.get('quiet_hours_start')
        quiet_end = request.POST.get('quiet_hours_end')
        if quiet_start:
            settings.quiet_hours_start = quiet_start
        if quiet_end:
            settings.quiet_hours_end = quiet_end
        
        # Notification types
        settings.lesson_complete = request.POST.get('lesson_complete', 'immediate')
        settings.quiz_passed = request.POST.get('quiz_passed', 'immediate')
        settings.streak_milestone = request.POST.get('streak_milestone', 'immediate')
        settings.weekly_summary = request.POST.get('weekly_summary', 'weekly')
        settings.inactivity_alert = request.POST.get('inactivity_alert', 'daily')
        
        settings.save()
        messages.success(request, "Notification settings updated!")
        return redirect('notification_settings')
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'learning/notification_settings.html', context)

@login_required
def lesson_detail(request, lesson_id):
    """Lesson detail view"""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    
    # Get or create progress record
    progress, created = ModuleProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson,
        defaults={'started_at': timezone.now()}
    )
    
    # Get quizzes for this lesson
    quizzes = lesson.quizzes.all().order_by('order')
    
    # Get user's quiz attempts
    quiz_attempts = {}
    if quizzes:
        attempts = QuizAttempt.objects.filter(
            student=request.user,
            quiz__in=quizzes
        )
        quiz_attempts = {attempt.quiz_id: attempt for attempt in attempts}
    
    context = {
        'lesson': lesson,
        'progress': progress,
        'quizzes': quizzes,
        'quiz_attempts': quiz_attempts,
    }
    
    return render(request, 'learning/lesson_detail.html', context)

@login_required
def download_lesson(request, lesson_id):
    """Download lesson file"""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    
    if not lesson.file:
        messages.error(request, 'No file available for download')
        return redirect('lesson_detail', lesson_id=lesson_id)
    
    # Record download
    download, created = LessonDownload.objects.get_or_create(
        student=request.user,
        lesson=lesson,
        defaults={
            'downloaded_at': timezone.now(),
            'file_size': lesson.file.size if lesson.file else 0
        }
    )
    
    # Serve file
    response = HttpResponse(lesson.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{lesson.file.name}"'
    return response

@login_required
@csrf_exempt
def submit_quiz(request, quiz_id):
    """Submit quiz answer"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    data = json.loads(request.body)
    selected_answer = data.get('answer')
    
    if not selected_answer:
        return JsonResponse({'error': 'No answer provided'}, status=400)
    
    # Check if correct
    is_correct = selected_answer == quiz.correct_answer
    
    # Save or update attempt
    attempt, created = QuizAttempt.objects.update_or_create(
        student=request.user,
        quiz=quiz,
        defaults={
            'selected_answer': selected_answer,
            'is_correct': is_correct,
            'attempted_at': timezone.now()
        }
    )
    
    # Update lesson progress
    lesson_quizzes = quiz.lesson.quizzes.all()
    user_attempts = QuizAttempt.objects.filter(
        student=request.user,
        quiz__in=lesson_quizzes
    )
    
    # Calculate score
    correct_attempts = user_attempts.filter(is_correct=True).count()
    total_quizzes = lesson_quizzes.count()
    score = (correct_attempts / total_quizzes * 100) if total_quizzes > 0 else 0
    
    # Update progress
    progress, created = ModuleProgress.objects.get_or_create(
        student=request.user,
        lesson=quiz.lesson
    )
    
    progress.score = score
    if user_attempts.count() == total_quizzes:  # All quizzes attempted
        progress.completed = True
        progress.completed_at = timezone.now()
    progress.save()
    
    return JsonResponse({
        'correct': is_correct,
        'correct_answer': quiz.correct_answer,
        'explanation': quiz.explanation,
        'score': score
    })

@login_required
def mark_lesson_complete(request, lesson_id):
    """Mark lesson as complete"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    
    progress, created = ModuleProgress.objects.get_or_create(
        student=request.user,
        lesson=lesson
    )
    
    progress.completed = True
    progress.completed_at = timezone.now()
    progress.save()
    
    return JsonResponse({'status': 'success'})

# PWA Views
def manifest(request):
    """Enhanced PWA manifest.json"""
    manifest_data = {
        "name": "Rural Digital Learning",
        "short_name": "Rural Edu",
        "description": "Empowering rural communities with digital literacy and education",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#4F46E5",
        "orientation": "portrait-primary",
        "categories": ["education", "learning", "rural"],
        "icons": [
            {
                "src": "/static/icons/icon-192x192.svg",
                "sizes": "192x192",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            },
            {
                "src": "/static/icons/icon-512x512.svg",
                "sizes": "512x512",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            }
        ],
        "shortcuts": [
            {
                "name": "Student Dashboard",
                "short_name": "Student",
                "description": "Access your learning dashboard",
                "url": "/student/",
                "icons": [
                    {
                        "src": "/static/icons/icon-192x192.svg",
                        "sizes": "192x192",
                        "type": "image/svg+xml"
                    }
                ]
            },
            {
                "name": "Teacher Dashboard",
                "short_name": "Teacher",
                "description": "Manage your classes and students",
                "url": "/teacher/",
                "icons": [
                    {
                        "src": "/static/icons/icon-192x192.svg",
                        "sizes": "192x192",
                        "type": "image/svg+xml"
                    }
                ]
            }
        ]
    }
    
    return JsonResponse(manifest_data)

def offline(request):
    """Offline page for PWA"""
    return render(request, 'learning/offline.html')

@staff_member_required
def admin_stats(request):
    """Admin dashboard statistics"""
    today = timezone.now().date()
    
    stats = {
        'total_users': User.objects.count(),
        'total_lessons': Lesson.objects.count(),
        'active_students': User.objects.filter(
            userprofile__role='student',
            is_active=True
        ).count(),
        'today_logins': LoginSession.objects.filter(
            login_time__date=today
        ).count(),
        'total_progress': ModuleProgress.objects.count(),
        'completed_lessons': ModuleProgress.objects.filter(completed=True).count(),
        'active_sessions': LoginSession.objects.filter(is_active=True).count(),
    }
    
    return JsonResponse(stats)

# Custom Admin Interface for Parents and Teachers
@login_required
def custom_admin_login(request):
    """Custom admin login for parents and teachers"""
    if request.user.is_authenticated:
        profile = get_object_or_404(UserProfile, user=request.user)
        if profile.role in ['parent', 'teacher']:
            return redirect('custom_admin_dashboard')
        else:
            messages.error(request, 'Access denied. Only parents and teachers can access this admin panel.')
            return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            profile = get_object_or_404(UserProfile, user=user)
            if profile.role in ['parent', 'teacher']:
                login(request, user)
                
                # Create login session record
                def get_client_ip(request):
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip = x_forwarded_for.split(',')[0]
                    else:
                        ip = request.META.get('REMOTE_ADDR')
                    return ip
                
                LoginSession.objects.create(
                    user=user,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    session_key=request.session.session_key
                )
                
                return redirect('custom_admin_dashboard')
            else:
                messages.error(request, 'Access denied. Only parents and teachers can access this admin panel.')
        else:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'learning/custom_admin_login.html')

@login_required
def custom_admin_dashboard(request):
    """Custom admin dashboard for parents and teachers"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if profile.role not in ['parent', 'teacher']:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    context = {
        'user_profile': profile,
        'total_students': 0,
        'total_lessons': Lesson.objects.filter(is_active=True).count(),
        'completed_lessons': 0,
        'recent_activities': [],
        'students': [],
    }
    
    if profile.role == 'teacher':
        # Teacher-specific data
        students = User.objects.filter(userprofile__role='student').select_related('userprofile')
        
        # Calculate student progress statistics
        total_progress = 0
        active_students = 0
        for student in students:
            progress_records = ModuleProgress.objects.filter(student=student)
            completed_count = progress_records.filter(completed=True).count()
            total_count = progress_records.count()
            if total_count > 0:
                total_progress += (completed_count / total_count * 100)
            if student.last_login:
                active_students += 1
        
        avg_progress = total_progress / students.count() if students.count() > 0 else 0
        
        context.update({
            'total_students': students.count(),
            'active_students': active_students,
            'avg_progress': round(avg_progress, 1),
            'students': students[:10],  # Show first 10 students
            'my_lessons': Lesson.objects.filter(created_by=request.user),
            'recent_progress': ModuleProgress.objects.select_related('student', 'lesson').order_by('-started_at')[:10]
        })
    elif profile.role == 'parent':
        # Parent-specific data
        children = User.objects.filter(userprofile__parent=profile).select_related('userprofile')
        
        # Calculate children progress
        children_progress_data = []
        for child in children:
            progress_records = ModuleProgress.objects.filter(student=child)
            completed_count = progress_records.filter(completed=True).count()
            total_count = progress_records.count()
            avg_score = progress_records.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0
            
            children_progress_data.append({
                'child': child,
                'completed_lessons': completed_count,
                'total_lessons': total_count,
                'avg_score': round(avg_score, 1),
                'progress_percentage': (completed_count / total_count * 100) if total_count > 0 else 0
            })
        
        context.update({
            'total_students': children.count(),
            'children': children,
            'children_detailed_progress': children_progress_data,
            'children_progress': ModuleProgress.objects.filter(student__in=children).select_related('student', 'lesson').order_by('-started_at')[:10]
        })
    
    return render(request, 'learning/custom_admin_dashboard.html', context)

@login_required
def custom_admin_lessons(request):
    """Lesson management for teachers"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if profile.role != 'teacher':
        messages.error(request, 'Access denied. Only teachers can manage lessons.')
        return redirect('custom_admin_dashboard')
    
    lessons = Lesson.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'lessons': lessons,
        'user_profile': profile,
    }
    
    return render(request, 'learning/custom_admin_lessons.html', context)

@login_required
def custom_admin_students(request):
    """Student monitoring for parents and teachers"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if profile.role not in ['parent', 'teacher']:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Apply filters
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    grade_filter = request.GET.get('grade', '')
    
    if profile.role == 'teacher':
        students = User.objects.filter(userprofile__role='student').select_related('userprofile')
    else:  # parent
        students = User.objects.filter(userprofile__parent=profile).select_related('userprofile')
    
    # Apply search filter
    if search:
        students = students.filter(
            Q(first_name__icontains=search) | 
            Q(last_name__icontains=search) | 
            Q(username__icontains=search)
        )
    
    # Apply status filter
    if status_filter == 'active':
        students = students.filter(last_login__isnull=False)
    elif status_filter == 'inactive':
        students = students.filter(last_login__isnull=True)
    
    # Calculate statistics and add progress data to each student
    students_with_progress = []
    total_progress = 0
    
    for student in students:
        progress_records = ModuleProgress.objects.filter(student=student)
        completed_count = progress_records.filter(completed=True).count()
        total_count = progress_records.count()
        progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
        
        # Add progress percentage to student's userprofile temporarily
        student.userprofile.progress_percentage = round(progress_percentage, 1)
        student.userprofile.completed_lessons = completed_count
        student.userprofile.total_lessons = total_count
        
        students_with_progress.append(student)
        total_progress += progress_percentage
    
    total_students = len(students_with_progress)
    active_students = students.filter(last_login__isnull=False).count()
    inactive_students = total_students - active_students
    avg_progress = total_progress / total_students if total_students > 0 else 0
    
    context = {
        'students': students_with_progress,
        'user_profile': profile,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'avg_progress': round(avg_progress, 1),
    }
    
    return render(request, 'learning/custom_admin_students.html', context)

@login_required
def custom_admin_add_lesson(request):
    """Add new lesson for teachers"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if profile.role != 'teacher':
        messages.error(request, 'Access denied. Only teachers can add lessons.')
        return redirect('custom_admin_dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        lesson_type = request.POST.get('lesson_type')
        language = request.POST.get('language')
        content = request.POST.get('content')
        video_url = request.POST.get('video_url')
        file = request.FILES.get('file')
        
        lesson = Lesson.objects.create(
            title=title,
            description=description,
            lesson_type=lesson_type,
            language=language,
            content=content,
            video_url=video_url,
            file=file,
            created_by=request.user,
            order=Lesson.objects.count() + 1
        )
        
        messages.success(request, f'Lesson "{lesson.title}" created successfully!')
        return redirect('custom_admin_lessons')
    
    context = {
        'user_profile': profile,
        'lesson_types': Lesson.LESSON_TYPE_CHOICES,
        'languages': Lesson.LANGUAGE_CHOICES,
    }
    
    return render(request, 'learning/custom_admin_add_lesson.html', context)


# Student CRUD Views
@login_required
def student_list(request):
    """List all students"""
    students = Student.objects.all().order_by('-created_at')
    
    context = {
        'students': students,
        'user_profile': getattr(request.user, 'userprofile', None),
    }
    return render(request, 'learning/student_list.html', context)


@login_required
def student_create(request):
    """Create a new student"""
    if request.method == 'POST':
        name = request.POST.get('name')
        age = request.POST.get('age')
        email = request.POST.get('email')
        course = request.POST.get('course')
        
        try:
            student = Student.objects.create(
                name=name,
                age=int(age),
                email=email,
                course=course
            )
            messages.success(request, f'Student "{student.name}" created successfully!')
            return redirect('student_list')
        except Exception as e:
            messages.error(request, f'Error creating student: {str(e)}')
    
    context = {
        'user_profile': getattr(request.user, 'userprofile', None),
    }
    return render(request, 'learning/student_form.html', context)


# Parent CRUD Views
@login_required
def parent_list(request):
    """List all parents"""
    parents = Parent.objects.all().order_by('-created_at')
    
    context = {
        'parents': parents,
        'user_profile': getattr(request.user, 'userprofile', None),
    }
    return render(request, 'learning/parent_list.html', context)


@login_required
def parent_create(request):
    """Create a new parent"""
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        relation = request.POST.get('relation')
        
        try:
            parent = Parent.objects.create(
                name=name,
                phone=phone,
                email=email,
                relation=relation
            )
            messages.success(request, f'Parent "{parent.name}" created successfully!')
            return redirect('parent_list')
        except Exception as e:
            messages.error(request, f'Error creating parent: {str(e)}')
    
    context = {
        'user_profile': getattr(request.user, 'userprofile', None),
    }
    return render(request, 'learning/parent_form.html', context)


# Teacher CRUD Views
@login_required
def teacher_list(request):
    """List all teachers"""
    teachers = Teacher.objects.all().order_by('-created_at')
    
    context = {
        'teachers': teachers,
        'user_profile': getattr(request.user, 'userprofile', None),
    }
    return render(request, 'learning/teacher_list.html', context)


@login_required
def teacher_create(request):
    """Create a new teacher"""
    if request.method == 'POST':
        name = request.POST.get('name')
        subject = request.POST.get('subject')
        email = request.POST.get('email')
        experience = request.POST.get('experience')
        
        try:
            teacher = Teacher.objects.create(
                name=name,
                subject=subject,
                email=email,
                experience=int(experience)
            )
            messages.success(request, f'Teacher "{teacher.name}" created successfully!')
            return redirect('teacher_list')
        except Exception as e:
            messages.error(request, f'Error creating teacher: {str(e)}')
    
    context = {
        'user_profile': getattr(request.user, 'userprofile', None),
    }
    return render(request, 'learning/teacher_form.html', context)
