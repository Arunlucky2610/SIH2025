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
import bcrypt

from .models import UserProfile, Lesson, ModuleProgress, Quiz, QuizAttempt, LessonDownload, LoginSession, Student, Parent, Teacher, QuizContainer, QuizContainerAttempt
from .teacher_communication_models import TeacherMessage
from .analytics import (
    get_progress_chart_data, get_subject_performance_data, get_learning_calendar_data,
    get_current_streak, update_all_analytics_for_student
)
from .notifications import NotificationService
from .mongodb_utils import (
    create_user_in_mongodb, get_user_by_username, update_user_login_session, 
    save_to_role_collection, check_username_exists_in_collections,
    authenticate_user_mongodb, get_user_from_role_collection
)

def get_unread_teacher_messages_count(user):
    """Get count of unread messages from teachers for a parent"""
    if hasattr(user, 'userprofile') and user.userprofile.role == 'parent':
        return TeacherMessage.objects.filter(
            recipient=user,
            is_read=False
        ).count()
    return 0

def home(request):
    """Landing page - redirect based on user role"""
    if request.user.is_authenticated:
        try:
            profile = request.user.userprofile
            if profile.role == 'student':
                return redirect('student_dashboard')
            elif profile.role == 'teacher':
                return redirect('teacher_home')
            elif profile.role == 'parent':
                return redirect('parent_dashboard')
        except UserProfile.DoesNotExist:
            # Create profile if doesn't exist
            UserProfile.objects.create(user=request.user, role='student')
            return redirect('student_dashboard')
    
    return render(request, 'learning/landing.html')

def user_login(request):
    """Clean login API that works for all real users"""
    
    if request.method == 'POST':
        from django.http import JsonResponse
        from django.contrib.auth import authenticate, login
        import json
        
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                # Parse JSON data
                data = json.loads(request.body)
                username_or_email = data.get('username', '').strip()
                password = data.get('password', '').strip()
                role = data.get('role', '').strip()
            else:
                # Handle form data
                username_or_email = request.POST.get('username', '').strip()
                password = request.POST.get('password', '').strip()
                role = request.POST.get('role', '').strip()
            
            # Validation
            if not username_or_email:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Username or email is required'
                })
                
            if not password:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Password is required'
                })
                
            if not role or role not in ['student', 'parent', 'teacher', 'admin']:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please select a valid role'
                })
            
            # Try to find user by username or email
            user = None
            try:
                # Check if input is email
                if '@' in username_or_email:
                    user = User.objects.get(email=username_or_email)
                else:
                    user = User.objects.get(username=username_or_email)
            except User.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Wrong username or password'
                })
            
            # Authenticate user with password
            authenticated_user = authenticate(request, username=user.username, password=password)
            
            if authenticated_user:
                # Check if user has correct role
                try:
                    profile = UserProfile.objects.get(user=authenticated_user)
                    if profile.role != role:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Wrong username or password'
                        })
                except UserProfile.DoesNotExist:
                    # Create profile if missing
                    UserProfile.objects.create(
                        user=authenticated_user,
                        role=role,
                        language_preference='en'
                    )
                
                # Log in the user
                login(request, authenticated_user)
                
                # Create login session record
                def get_client_ip(request):
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip = x_forwarded_for.split(',')[0]
                    else:
                        ip = request.META.get('REMOTE_ADDR')
                    return ip
                
                try:
                    LoginSession.objects.create(
                        user=authenticated_user,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        session_key=request.session.session_key
                    )
                except Exception as e:
                    pass  # Don't let session tracking errors break login
                
                # Return success with dashboard URL
                dashboard_urls = {
                    'student': '/student/',
                    'parent': '/parent/',
                    'teacher': '/teacher/',
                    'admin': '/admin/'
                }
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Welcome back, {authenticated_user.first_name or authenticated_user.username}!',
                    'redirect_url': dashboard_urls.get(role, '/')
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Wrong username or password'
                })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred during login'
            })
    
    # GET request - render login form
    return render(request, 'learning/login.html')

def user_signup(request):
    """Clean signup API that works for all real users and roles"""
    
    if request.method == 'POST':
        from django.http import JsonResponse
        import json
        
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                # Parse JSON data
                data = json.loads(request.body)
                role = data.get('role', '').strip().lower()
            else:
                # Handle form data
                data = request.POST
                role = data.get('role', '').strip().lower()
            
            # Extract role-specific data
            if role == 'student':
                username = data.get('student_username', '').strip()
                password = data.get('student_password', '').strip()
                email = data.get('student_email', '').strip() or f"{username}@student.rural-learning.com"
                first_name = data.get('student_first_name', '').strip()
                last_name = data.get('student_last_name', '').strip()
                
            elif role == 'parent':
                username = data.get('parent_username', '').strip()
                password = data.get('parent_password', '').strip()
                email = data.get('parent_email', '').strip()
                first_name = data.get('parent_full_name', '').strip()
                last_name = ''
                
            elif role == 'teacher':
                username = data.get('teacher_username', '').strip()
                password = data.get('teacher_password', '').strip()
                email = data.get('teacher_email', '').strip()
                first_name = data.get('teacher_name', '').strip()
                last_name = ''
                
            elif role == 'admin':
                username = data.get('admin_username', '').strip()
                password = data.get('admin_password', '').strip()
                email = data.get('admin_email', '').strip()
                first_name = data.get('admin_name', '').strip()
                last_name = ''
                
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please select a valid role'
                })
            
            # Validation
            if not username:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Username is required'
                })
                
            if len(username) < 3:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Username must be at least 3 characters long'
                })
                
            if not email:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Email is required'
                })
                
            if '@' not in email or '.' not in email.split('@')[-1]:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please enter a valid email address'
                })
                
            if not password:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Password is required'
                })
                
            if len(password) < 6:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Password must be at least 6 characters long'
                })
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Username already exists'
                })
                
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Email already exists'
                })
            
            # Create user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create UserProfile with role
            UserProfile.objects.create(
                user=user,
                role=role,
                language_preference='en'
            )
            
            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': 'Account created successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            })
    
    # GET request - render signup form
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
    
    # Get available quizzes
    available_quizzes = QuizContainer.objects.filter(
        is_active=True
    ).order_by('-created_at')[:10]
    
    # Get quiz attempts for this student
    quiz_attempts = QuizContainerAttempt.objects.filter(
        student=request.user
    ).select_related('quiz_container')
    
    # Add attempt info to each quiz
    for quiz in available_quizzes:
        quiz.user_attempt = quiz_attempts.filter(quiz_container=quiz).first()
    
    context = {
        'lessons': lessons,
        'progress_dict': progress_dict,
        'total_lessons': total_lessons,
        'completed_lessons': completed_lessons,
        'progress_percentage': progress_percentage,
        'recent_downloads': recent_downloads,
        'available_quizzes': available_quizzes,
        'quiz_attempts': quiz_attempts,
        'user_profile': profile,  # Template expects 'user_profile' not 'profile'
    }
    
    return render(request, 'learning/student_dashboard.html', context)

@login_required
def teacher_home(request):
    """Teacher home page - overview and quick actions"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'teacher' and not request.user.is_staff:
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Basic stats for teacher home
    total_students = User.objects.filter(userprofile__role='student').count()
    my_lessons = Lesson.objects.filter(created_by=request.user).count()
    
    # Recent activity - last 5 quiz attempts
    recent_quiz_attempts = QuizAttempt.objects.select_related(
        'student', 'quiz__lesson'
    ).order_by('-attempted_at')[:5]
    
    # Today's completed lessons
    today = timezone.now().date()
    today_completions = ModuleProgress.objects.filter(
        completed=True,
        completed_at__date=today
    ).select_related('student', 'lesson').count()
    
    # Quick actions data
    pending_quizzes = Quiz.objects.filter(lesson__created_by=request.user).count()
    
    # Recent quizzes created by teacher
    try:
        from .models import QuizContainer
        recent_quizzes = QuizContainer.objects.filter(created_by=request.user).order_by('-created_at')[:5]
        # Force query evaluation to avoid any caching issues
        recent_quizzes = list(recent_quizzes)
    except:
        recent_quizzes = []  # In case QuizContainer model doesn't exist yet
    
    context = {
        'profile': profile,
        'total_students': total_students,
        'my_lessons': my_lessons,
        'recent_quiz_attempts': recent_quiz_attempts,
        'today_completions': today_completions,
        'pending_quizzes': pending_quizzes,
        'recent_quizzes': recent_quizzes,
        'today': today,
    }
    
    return render(request, 'learning/teacher_home.html', context)

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
        
        # Calculate average score from quiz attempts
        quiz_attempts = QuizAttempt.objects.filter(student=student)
        if quiz_attempts.exists():
            correct_attempts = quiz_attempts.filter(is_correct=True).count()
            total_attempts = quiz_attempts.count()
            avg_score = (correct_attempts / total_attempts) * 100 if total_attempts > 0 else 0
        else:
            # Fallback to ModuleProgress scores
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
    
    # Weekly progress data for chart
    today = timezone.now().date()
    weekly_data = []
    weekly_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    for i in range(7):
        day_date = today - timedelta(days=today.weekday()) + timedelta(days=i)
        
        # Get quiz attempts for this day and calculate percentage of correct answers
        day_attempts = QuizAttempt.objects.filter(attempted_at__date=day_date)
        if day_attempts.exists():
            correct_count = day_attempts.filter(is_correct=True).count()
            total_attempts = day_attempts.count()
            quiz_percentage = (correct_count / total_attempts) * 100 if total_attempts > 0 else 0
        else:
            quiz_percentage = 0
        
        # Get module progress for this day
        day_progress = ModuleProgress.objects.filter(
            completed_at__date=day_date,
            completed=True
        ).count()
        
        # Calculate daily progress percentage based on completed modules
        total_students = students.count()
        progress_percentage = (day_progress / max(1, total_students)) * 100 if total_students > 0 else 0
        
        # Use average of quiz performance and progress completion
        if quiz_percentage > 0 and progress_percentage > 0:
            daily_percentage = (quiz_percentage + progress_percentage) / 2
        elif quiz_percentage > 0:
            daily_percentage = quiz_percentage
        elif progress_percentage > 0:
            daily_percentage = progress_percentage
        else:
            daily_percentage = 0
        
        weekly_data.append({
            'day': weekly_labels[i],
            'percentage': round(min(100, daily_percentage), 1),
            'date': day_date
        })
    
    # Calculate weekly average
    weekly_average = sum(day['percentage'] for day in weekly_data) / 7 if weekly_data else 0
    
    # Find best day
    best_day = max(weekly_data, key=lambda x: x['percentage']) if weekly_data else {'day': 'N/A', 'percentage': 0}
    
    context = {
        'students': students,
        'lessons': lessons,
        'progress_summary': progress_summary,
        'recent_attempts': recent_attempts,
        'profile': profile,
        'today': timezone.now().date(),
        'weekly_data': weekly_data,
        'weekly_average': round(weekly_average, 1),
        'best_day': best_day,
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
        # Teacher Communication data
        'unread_messages_count': get_unread_teacher_messages_count(request.user),
    }
    
    return render(request, 'learning/parent_dashboard_ultra.html', context)


@login_required
def study_schedule(request):
    """Study schedule page for parents"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'parent':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get children (students linked to this parent)
    children = UserProfile.objects.filter(parent=profile)
    
    context = {
        'user': request.user,
        'profile': profile,
        'children': children,
    }
    
    return render(request, 'learning/study_schedule.html', context)


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
def analytics_page(request):
    """Dedicated analytics page for detailed learning insights"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'parent':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get children (students linked to this parent)
    children = UserProfile.objects.filter(parent=profile)
    
    context = {
        'profile': profile,
        'children_count': len(children),
    }
    
    return render(request, 'learning/analytics.html', context)


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
    
    # Serve file for download
    response = HttpResponse(lesson.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{lesson.file.name}"'
    return response

@login_required
def view_lesson_file(request, lesson_id):
    """View lesson file online in browser"""
    lesson = get_object_or_404(Lesson, id=lesson_id, is_active=True)
    
    if not lesson.file:
        messages.error(request, 'No file available for viewing')
        return redirect('lesson_detail', lesson_id=lesson_id)
    
    # Get file extension to determine content type
    import os
    file_name = lesson.file.name
    file_extension = os.path.splitext(file_name)[1].lower()
    
    # Define content types for different file types
    content_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
    }
    
    content_type = content_types.get(file_extension, 'application/octet-stream')
    
    # For PDFs and images, display inline. For others, try to display or fallback to download
    if file_extension in ['.pdf', '.txt', '.jpg', '.jpeg', '.png', '.gif', '.svg']:
        disposition = 'inline'
    else:
        disposition = 'attachment'
    
    # Serve file for viewing
    try:
        response = HttpResponse(lesson.file.read(), content_type=content_type)
        response['Content-Disposition'] = f'{disposition}; filename="{os.path.basename(file_name)}"'
        return response
    except Exception as e:
        messages.error(request, f'Error viewing file: {str(e)}')
        return redirect('lesson_detail', lesson_id=lesson_id)

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

@login_required
def teacher_reports(request):
    """Teacher reports and analytics dashboard"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if profile.role != 'teacher' and not request.user.is_staff:
        messages.error(request, 'Access denied. Only teachers can view reports.')
        return redirect('home')
    
    today = timezone.now().date()
    
    # Get students data
    students = User.objects.filter(userprofile__role='student').select_related('userprofile')
    
    # Get lessons created by this teacher
    teacher_lessons = Lesson.objects.filter(created_by=request.user)
    
    # Overall statistics
    stats = {
        'total_students': students.count(),
        'active_students': students.filter(is_active=True).count(),
        'total_lessons': teacher_lessons.count(),
        'total_progress_records': ModuleProgress.objects.count(),
        'completed_lessons_total': ModuleProgress.objects.filter(completed=True).count(),
        'total_quiz_attempts': QuizAttempt.objects.count(),
        'correct_quiz_attempts': QuizAttempt.objects.filter(is_correct=True).count(),
    }
    
    # Calculate completion rate
    if stats['total_progress_records'] > 0:
        stats['completion_rate'] = (stats['completed_lessons_total'] / stats['total_progress_records']) * 100
    else:
        stats['completion_rate'] = 0
    
    # Calculate quiz accuracy
    if stats['total_quiz_attempts'] > 0:
        stats['quiz_accuracy'] = (stats['correct_quiz_attempts'] / stats['total_quiz_attempts']) * 100
    else:
        stats['quiz_accuracy'] = 0
    
    # Recent activity (last 7 days)
    week_ago = today - timedelta(days=7)
    recent_progress = ModuleProgress.objects.filter(
        started_at__date__gte=week_ago
    ).order_by('-started_at')[:20]
    
    recent_quiz_attempts = QuizAttempt.objects.filter(
        attempted_at__date__gte=week_ago
    ).select_related('student', 'quiz__lesson').order_by('-attempted_at')[:20]
    
    # Student performance data
    student_performance = []
    for student in students[:10]:  # Top 10 students for performance view
        progress_records = ModuleProgress.objects.filter(student=student)
        completed = progress_records.filter(completed=True).count()
        total = progress_records.count()
        
        quiz_attempts = QuizAttempt.objects.filter(student=student)
        correct_quizzes = quiz_attempts.filter(is_correct=True).count()
        total_quizzes = quiz_attempts.count()
        
        student_performance.append({
            'student': student,
            'completed_lessons': completed,
            'total_lessons': total,
            'completion_rate': (completed / total * 100) if total > 0 else 0,
            'quiz_accuracy': (correct_quizzes / total_quizzes * 100) if total_quizzes > 0 else 0,
            'total_quiz_attempts': total_quizzes,
        })
    
    # Lesson popularity data
    lesson_stats = []
    for lesson in teacher_lessons:
        progress_count = ModuleProgress.objects.filter(lesson=lesson).count()
        completed_count = ModuleProgress.objects.filter(lesson=lesson, completed=True).count()
        
        lesson_stats.append({
            'lesson': lesson,
            'total_enrollments': progress_count,
            'completions': completed_count,
            'completion_rate': (completed_count / progress_count * 100) if progress_count > 0 else 0,
        })
    
    context = {
        'profile': profile,
        'stats': stats,
        'recent_progress': recent_progress,
        'recent_quiz_attempts': recent_quiz_attempts,
        'student_performance': student_performance,
        'lesson_stats': lesson_stats,
        'teacher_lessons': teacher_lessons,
    }
    
    return render(request, 'learning/teacher_reports.html', context)

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
def student_detail_view(request, student_id):
    """Detailed view of a specific student's progress and activities"""
    profile = get_object_or_404(UserProfile, user=request.user)
    
    if profile.role not in ['parent', 'teacher']:
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    # Get the student
    student = get_object_or_404(User, id=student_id, userprofile__role='student')
    student_profile = student.userprofile
    
    # Check permission - parents can only view their children
    if profile.role == 'parent' and student_profile.parent != profile:
        messages.error(request, 'You can only view your own children.')
        return redirect('custom_admin_students')
    
    # Get student progress data
    progress_records = ModuleProgress.objects.filter(student=student).select_related('lesson')
    completed_count = progress_records.filter(completed=True).count()
    total_count = progress_records.count()
    progress_percentage = (completed_count / total_count * 100) if total_count > 0 else 0
    
    # Get quiz attempts
    quiz_attempts = QuizAttempt.objects.filter(student=student).select_related('quiz__lesson').order_by('-attempted_at')
    correct_attempts = quiz_attempts.filter(is_correct=True).count()
    total_quiz_attempts = quiz_attempts.count()
    quiz_accuracy = (correct_attempts / total_quiz_attempts * 100) if total_quiz_attempts > 0 else 0
    
    # Get recent activity (last 10 items)
    recent_progress = progress_records.order_by('-started_at')[:10]
    recent_quizzes = quiz_attempts[:10]
    
    # Get learning streak and time spent
    learning_streak = 0
    total_time_spent = timedelta(0)
    
    for progress in progress_records:
        if progress.time_spent:
            total_time_spent += progress.time_spent
    
    # Calculate learning streak (consecutive days with activity)
    if progress_records.exists():
        last_activity = progress_records.order_by('-started_at').first().started_at.date()
        current_date = timezone.now().date()
        
        # Simple streak calculation - count days back from today
        streak_date = current_date
        while streak_date >= last_activity:
            day_activity = progress_records.filter(started_at__date=streak_date).exists()
            if day_activity:
                learning_streak += 1
                streak_date -= timedelta(days=1)
            else:
                break
    
    # Get lessons breakdown by type
    lesson_types = {}
    for progress in progress_records:
        lesson_type = progress.lesson.get_lesson_type_display()
        if lesson_type not in lesson_types:
            lesson_types[lesson_type] = {'total': 0, 'completed': 0}
        lesson_types[lesson_type]['total'] += 1
        if progress.completed:
            lesson_types[lesson_type]['completed'] += 1
    
    context = {
        'student': student,
        'student_profile': student_profile,
        'user_profile': profile,
        'completed_count': completed_count,
        'total_count': total_count,
        'progress_percentage': round(progress_percentage, 1),
        'quiz_accuracy': round(quiz_accuracy, 1),
        'total_quiz_attempts': total_quiz_attempts,
        'learning_streak': learning_streak,
        'total_time_spent': total_time_spent,
        'recent_progress': recent_progress,
        'recent_quizzes': recent_quizzes,
        'lesson_types': lesson_types,
        'progress_records': progress_records,
    }
    
    return render(request, 'learning/student_detail.html', context)

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

@login_required
def student_schedule(request):
    """Student schedule page with professional design"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'student':
        messages.error(request, 'Access denied')
        return redirect('home')

    context = {
        'user': request.user,
        'profile': profile,
    }
    return render(request, 'learning/student_schedule.html', context)

@login_required
def send_message(request):
    """Send a message to a student"""
    if request.method == 'POST':
        try:
            import json
            from django.http import JsonResponse
            from .notification_models import Notification
            
            # Parse JSON data
            data = json.loads(request.body)
            student_id = data.get('student_id')
            subject = data.get('subject')
            message_type = data.get('message_type')
            content = data.get('content')
            notify_parent = data.get('notify_parent', False)
            
            # Get the student
            student = get_object_or_404(User, id=student_id, userprofile__role='student')
            
            # Check permission
            user_profile = get_object_or_404(UserProfile, user=request.user)
            if user_profile.role not in ['teacher', 'parent']:
                return JsonResponse({'success': False, 'error': 'Permission denied'})
            
            # Create notification for student
            notification = Notification.objects.create(
                recipient=student,
                sender=request.user,
                title=f"{message_type.title()}: {subject}",
                message=content,
                notification_type=message_type,
                is_read=False
            )
            
            # If notify parent is checked, also send to parent
            if notify_parent and hasattr(student.userprofile, 'parent') and student.userprofile.parent:
                parent_user = student.userprofile.parent.user
                Notification.objects.create(
                    recipient=parent_user,
                    sender=request.user,
                    title=f"Message about {student.get_full_name()}: {subject}",
                    message=f"Message sent to your child:\n\n{content}",
                    notification_type=message_type,
                    is_read=False
                )
            
            return JsonResponse({'success': True, 'message': 'Message sent successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def create_quiz(request):
    """Create a new quiz"""
    # Check permission first
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'teacher':
        messages.error(request, 'Only teachers can create quizzes.')
        return redirect('teacher_dashboard')
    
    if request.method == 'POST':
        try:
            # Check if it's an AJAX request with JSON data
            if request.content_type == 'application/json':
                import json
                # Parse JSON data for AJAX requests
                data = json.loads(request.body)
                title = data.get('title')
                quiz_type = data.get('quiz_type')
                description = data.get('description', '')
                duration = data.get('duration', 30)
                difficulty = data.get('difficulty', 'medium')
                randomize_questions = data.get('randomize_questions', False)
                show_results = data.get('show_results', True)
                
                # Create quiz
                from .models import QuizContainer
                quiz = QuizContainer.objects.create(
                    title=title,
                    description=description,
                    quiz_type=quiz_type,
                    duration=duration,
                    difficulty=difficulty,
                    randomize_questions=randomize_questions,
                    show_results=show_results,
                    created_by=request.user,
                    is_active=True  # Create as active quiz
                )
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Quiz created successfully',
                    'quiz_id': quiz.id
                })
            else:
                # Handle regular form submission
                title = request.POST.get('quiz_title')
                quiz_type = request.GET.get('type', 'quick')
                description = request.POST.get('quiz_description', '')
                duration = int(request.POST.get('quiz_duration', 30))
                
                if not title:
                    messages.error(request, 'Quiz title is required.')
                    return redirect('create_quiz')
                
                # Create quiz
                from .models import QuizContainer
                quiz = QuizContainer.objects.create(
                    title=title,
                    description=description,
                    quiz_type=quiz_type,
                    duration=duration,
                    difficulty='medium',
                    randomize_questions=False,
                    show_results=True,
                    created_by=request.user,
                    is_active=True  # Create as active quiz
                )
                
                messages.success(request, f'Quiz "{title}" created successfully!')
                return redirect('teacher_home')
                
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'success': False, 'error': str(e)})
            else:
                messages.error(request, f'Error creating quiz: {str(e)}')
                return redirect('create_quiz')
    
    # Handle GET request - show quiz creation form
    context = {
        'quiz_type': request.GET.get('type', 'quick'),  # Default to quick quiz
        'user_profile': user_profile
    }
    return render(request, 'learning/create_quiz.html', context)

@login_required
def publish_quiz(request, quiz_id):
    """Publish a quiz to make it available to students"""
    if request.method == 'POST':
        try:
            # Check permission
            user_profile = get_object_or_404(UserProfile, user=request.user)
            if user_profile.role != 'teacher':
                return JsonResponse({'success': False, 'error': 'Only teachers can publish quizzes'})
            
            # Get and publish quiz
            from .models import QuizContainer
            quiz = get_object_or_404(QuizContainer, id=quiz_id, created_by=request.user)
            quiz.is_active = True
            quiz.save()
            
            return JsonResponse({'success': True, 'message': 'Quiz published successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@login_required
def delete_quiz(request, quiz_id):
    """Delete a quiz with confirmation page"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"delete_quiz view called - Method: {request.method}, User: {request.user.id}, Quiz ID: {quiz_id}")
    
    # Check permission
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'teacher':
        messages.error(request, 'Only teachers can delete quizzes.')
        return redirect('teacher_home')
    
    # Get quiz
    from .models import QuizContainer
    quiz = get_object_or_404(QuizContainer, id=quiz_id)
    
    # Check if teacher is the creator of this quiz
    if quiz.created_by != request.user:
        messages.error(request, 'You can only delete quizzes you created.')
        return redirect('teacher_home')
    
    if request.method == 'GET':
        # Show confirmation page
        context = {
            'quiz': quiz,
            'user_profile': user_profile,
        }
        return render(request, 'learning/delete_quiz_confirm.html', context)
    
    elif request.method == 'POST':
        try:
            # Double-check that quiz still exists and user has permission
            if not QuizContainer.objects.filter(id=quiz_id, created_by=request.user).exists():
                logger.error(f"Quiz {quiz_id} not found or user {request.user.id} lacks permission")
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'message': 'Quiz not found or you do not have permission to delete it'
                })
            
            logger.info(f"Starting deletion of quiz {quiz_id}")
            quiz_title = quiz.title
            
            logger.info(f"Deleting quiz: {quiz_title}")
            logger.info(f"Quiz exists before deletion: {QuizContainer.objects.filter(id=quiz_id).exists()}")
            
            # Manual cascade delete for better performance and control
            from django.db import transaction
            
            with transaction.atomic():
                # Log what we're deleting
                from .models import QuizAttempt, QuizContainerAttempt
                quiz_attempts_count = QuizAttempt.objects.filter(quiz__quiz_container=quiz).count()
                container_attempts_count = QuizContainerAttempt.objects.filter(quiz_container=quiz).count()
                questions_count = quiz.quiz_questions.count()
                
                logger.info(f"Deleting {quiz_attempts_count} quiz attempts")
                logger.info(f"Deleting {container_attempts_count} container attempts")
                logger.info(f"Deleting {questions_count} questions")
                
                # Delete the quiz container - Django will handle CASCADE deletion
                quiz.delete()
                
            logger.info(f"Successfully deleted quiz: {quiz_title}")
            logger.info(f"Quiz exists after deletion: {QuizContainer.objects.filter(id=quiz_id).exists()}")
            
            # Return JSON response for AJAX handling
            from django.http import JsonResponse
            return JsonResponse({
                'success': True,
                'message': 'Quiz deleted successfully',
                'redirect_url': '/teacher/'
            })
            
        except Exception as e:
            import traceback
            logger.error(f"Error deleting quiz {quiz_id}: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            from django.http import JsonResponse
            return JsonResponse({
                'success': False,
                'message': f'Error deleting quiz: {str(e)}',
                'error_type': type(e).__name__
            })

@login_required
def delete_lesson(request, lesson_id):
    """Delete a lesson with confirmation page"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"delete_lesson view called - Method: {request.method}, User: {request.user.id}, Lesson ID: {lesson_id}")
    
    # Check permission
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'teacher':
        messages.error(request, 'Only teachers can delete lessons.')
        return redirect('custom_admin_lessons')
    
    # Get lesson
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Check if teacher is the creator of this lesson
    if lesson.created_by != request.user:
        messages.error(request, 'You can only delete lessons you created.')
        return redirect('custom_admin_lessons')
    
    if request.method == 'GET':
        # Show confirmation page
        context = {
            'lesson': lesson,
            'user_profile': user_profile,
        }
        return render(request, 'learning/delete_lesson_confirm.html', context)
    
    elif request.method == 'POST':
        try:
            logger.info(f"Starting deletion of lesson {lesson_id}")
            lesson_title = lesson.title
            
            logger.info(f"Deleting lesson: {lesson_title}")
            
            # Manual cascade delete for better performance and control
            from django.db import transaction
            
            with transaction.atomic():
                # Delete related records first to avoid cascade overhead
                lesson.student_progress.all().delete()
                lesson.quizzes.all().delete() 
                lesson.downloads.all().delete()
                
                # Also delete any LearningActivity records
                from .models import LearningActivity
                LearningActivity.objects.filter(lesson=lesson).delete()
                
                # Finally delete the lesson itself
                lesson.delete()
                
            logger.info(f"Successfully deleted lesson: {lesson_title}")
            
            # Redirect back to manage lessons without success message
            return redirect('custom_admin_lessons')
            
        except Exception as e:
            logger.error(f"Error deleting lesson {lesson_id}: {str(e)}")
            messages.error(request, f'Error deleting lesson: {str(e)}')
            return redirect('custom_admin_lessons')
    
    return redirect('custom_admin_lessons')

@login_required
def edit_quiz(request, quiz_id):
    """Edit quiz page"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'teacher':
        messages.error(request, 'Only teachers can edit quizzes.')
        return redirect('teacher_home')
    
    try:
        from .models import QuizContainer
        quiz = get_object_or_404(QuizContainer, id=quiz_id, created_by=request.user)
        
        context = {
            'quiz': quiz,
            'user_profile': user_profile,
        }
        
        return render(request, 'learning/edit_quiz.html', context)
        
    except Exception as e:
        messages.error(request, f'Error loading quiz: {str(e)}')
        return redirect('teacher_home')

@login_required
def create_quick_quiz(request):
    """Create quick quiz page"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'teacher':
        messages.error(request, 'Only teachers can create quizzes.')
        return redirect('teacher_home')
    
    if request.method == 'POST':
        try:
            # Get quiz details
            quiz_title = request.POST.get('quiz_title')
            quiz_description = request.POST.get('quiz_description', '')
            
            # Create quiz container
            from .models import QuizContainer
            quiz_container = QuizContainer.objects.create(
                title=quiz_title,
                description=quiz_description,
                quiz_type='quick',
                duration=30,  # Default 30 minutes for quick quiz
                created_by=request.user,
                is_active=True  # Quick quizzes are immediately active
            )
            
            # Process questions
            question_count = 0
            for key in request.POST.keys():
                if key.startswith('question_'):
                    question_num = key.split('_')[1]
                    question_text = request.POST.get(f'question_{question_num}')
                    option_a = request.POST.get(f'option_a_{question_num}')
                    option_b = request.POST.get(f'option_b_{question_num}')
                    option_c = request.POST.get(f'option_c_{question_num}')
                    option_d = request.POST.get(f'option_d_{question_num}')
                    correct_answer = request.POST.get(f'correct_answer_{question_num}')
                    
                    if question_text and option_a and option_b and option_c and option_d and correct_answer:
                        # Create quiz question
                        Quiz.objects.create(
                            quiz_container=quiz_container,
                            question=question_text,
                            option_a=option_a,
                            option_b=option_b,
                            option_c=option_c,
                            option_d=option_d,
                            correct_answer=correct_answer,
                            order=question_count + 1
                        )
                        question_count += 1
            
            messages.success(request, f'Quick quiz "{quiz_title}" created successfully with {question_count} questions!')
            return redirect('teacher_home')
            
        except Exception as e:
            messages.error(request, f'Error creating quiz: {str(e)}')
    
    context = {
        'user_profile': user_profile,
        'quiz_type': 'quick'
    }
    return render(request, 'learning/create_quiz.html', context)

@login_required
def schedule_quiz(request):
    """Schedule quiz page"""
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'teacher':
        messages.error(request, 'Only teachers can create quizzes.')
        return redirect('teacher_home')
    
    if request.method == 'POST':
        try:
            # Get quiz details
            quiz_title = request.POST.get('quiz_title')
            quiz_description = request.POST.get('quiz_description', '')
            quiz_duration = request.POST.get('quiz_duration', 60)
            schedule_date = request.POST.get('schedule_date')
            schedule_time = request.POST.get('schedule_time')
            
            # Create quiz container
            from .models import QuizContainer
            quiz_container = QuizContainer.objects.create(
                title=quiz_title,
                description=quiz_description,
                quiz_type='assignment',
                duration=int(quiz_duration),
                created_by=request.user,
                is_active=False  # Scheduled quizzes start as inactive
            )
            
            # Process questions (same as quick quiz)
            question_count = 0
            for key in request.POST.keys():
                if key.startswith('question_'):
                    question_num = key.split('_')[1]
                    question_text = request.POST.get(f'question_{question_num}')
                    option_a = request.POST.get(f'option_a_{question_num}')
                    option_b = request.POST.get(f'option_b_{question_num}')
                    option_c = request.POST.get(f'option_c_{question_num}')
                    option_d = request.POST.get(f'option_d_{question_num}')
                    correct_answer = request.POST.get(f'correct_answer_{question_num}')
                    
                    if question_text and option_a and option_b and option_c and option_d and correct_answer:
                        Quiz.objects.create(
                            quiz_container=quiz_container,
                            question=question_text,
                            option_a=option_a,
                            option_b=option_b,
                            option_c=option_c,
                            option_d=option_d,
                            correct_answer=correct_answer,
                            order=question_count + 1
                        )
                        question_count += 1
            
            messages.success(request, f'Quiz "{quiz_title}" scheduled successfully with {question_count} questions!')
            return redirect('teacher_home')
            
        except Exception as e:
            messages.error(request, f'Error scheduling quiz: {str(e)}')
    
    context = {
        'user_profile': user_profile,
        'quiz_type': 'schedule'
    }
    return render(request, 'learning/create_quiz.html', context)

@login_required
def take_quiz(request, quiz_id):
    """Take a quiz"""
    quiz_container = get_object_or_404(QuizContainer, id=quiz_id, is_active=True)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if user_profile.role != 'student':
        messages.error(request, 'Only students can take quizzes.')
        return redirect('home')
    
    # Check if student has already completed this quiz
    existing_attempt = QuizContainerAttempt.objects.filter(
        student=request.user,
        quiz_container=quiz_container,
        is_completed=True
    ).first()
    
    if existing_attempt:
        messages.info(request, f'You have already completed this quiz with a score of {existing_attempt.percentage}%')
        return redirect('student_dashboard')
    
    # Get all questions for this quiz
    questions = Quiz.objects.filter(quiz_container=quiz_container).order_by('order')
    
    if not questions.exists():
        messages.error(request, 'This quiz has no questions.')
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        # Process quiz submission
        score = 0
        total_questions = questions.count()
        
        # Create or get quiz container attempt
        container_attempt, created = QuizContainerAttempt.objects.get_or_create(
            student=request.user,
            quiz_container=quiz_container,
            defaults={
                'total_questions': total_questions,
                'started_at': timezone.now()
            }
        )
        
        # Process each question
        for question in questions:
            selected_answer = request.POST.get(f'question_{question.id}')
            if selected_answer:
                is_correct = selected_answer == question.correct_answer
                if is_correct:
                    score += 1
                
                # Save individual question attempt
                QuizAttempt.objects.update_or_create(
                    student=request.user,
                    quiz=question,
                    defaults={
                        'selected_answer': selected_answer,
                        'is_correct': is_correct,
                        'attempted_at': timezone.now()
                    }
                )
        
        # Update container attempt
        percentage = (score / total_questions * 100) if total_questions > 0 else 0
        container_attempt.score = score
        container_attempt.percentage = percentage
        container_attempt.completed_at = timezone.now()
        container_attempt.is_completed = True
        container_attempt.save()
        
        messages.success(request, f'Quiz completed! You scored {score}/{total_questions} ({percentage:.1f}%)')
        return redirect('quiz_result', attempt_id=container_attempt.id)
    
    context = {
        'quiz_container': quiz_container,
        'questions': questions,
        'user_profile': user_profile,
    }
    return render(request, 'learning/take_quiz.html', context)

@login_required 
def quiz_result(request, attempt_id):
    """Show quiz results"""
    attempt = get_object_or_404(QuizContainerAttempt, id=attempt_id, student=request.user)
    
    # Get detailed question results
    question_attempts = QuizAttempt.objects.filter(
        student=request.user,
        quiz__quiz_container=attempt.quiz_container
    ).select_related('quiz')
    
    context = {
        'attempt': attempt,
        'question_attempts': question_attempts,
    }
    return render(request, 'learning/quiz_result.html', context)
