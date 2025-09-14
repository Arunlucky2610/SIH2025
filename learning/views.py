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

from .models import UserProfile, Lesson, ModuleProgress, Quiz, QuizAttempt, LessonDownload, LoginSession

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
    """User signup view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        role = request.POST.get('role', 'student')
        language = request.POST.get('language', 'en')
        phone = request.POST.get('phone')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'learning/signup.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'learning/signup.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )
        
        # Create profile
        UserProfile.objects.create(
            user=user,
            role=role,
            language_preference=language,
            phone_number=phone
        )
        
        messages.success(request, 'Account created successfully')
        return redirect('login')
    
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
    """Parent dashboard view"""
    profile = get_object_or_404(UserProfile, user=request.user)
    if profile.role != 'parent':
        messages.error(request, 'Access denied')
        return redirect('home')
    
    # Get children (students linked to this parent)
    children = UserProfile.objects.filter(parent=profile)
    
    children_progress = []
    for child_profile in children:
        child = child_profile.user
        progress = ModuleProgress.objects.filter(student=child)
        completed_count = progress.filter(completed=True).count()
        total_count = progress.count()
        avg_score = progress.filter(score__isnull=False).aggregate(Avg('score'))['score__avg'] or 0
        
        # Recent activity
        recent_progress = progress.order_by('-started_at')[:5]
        
        children_progress.append({
            'child': child,
            'profile': child_profile,
            'completed_lessons': completed_count,
            'total_lessons': total_count,
            'avg_score': round(avg_score, 1),
            'progress_percentage': (completed_count / total_count * 100) if total_count > 0 else 0,
            'recent_progress': recent_progress,
        })
    
    context = {
        'children_progress': children_progress,
        'profile': profile,
    }
    
    return render(request, 'learning/parent_dashboard.html', context)

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
