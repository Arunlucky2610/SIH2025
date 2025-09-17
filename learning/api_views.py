from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, login
from django.utils import timezone
from .models import (
    Lesson, UserProfile, ModuleProgress, 
    LearningStreak, LessonDownload
)
import json

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard_data(request):
    """
    API endpoint to get student dashboard data
    """
    try:
        user = request.user
        
        # Get user profile
        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            profile = None
        
        # Get all lessons
        lessons = Lesson.objects.all()
        
        # Get user progress
        progress_records = ModuleProgress.objects.filter(student=user)
        progress_dict = {p.lesson_id: p for p in progress_records}
        
        # Calculate stats
        total_lessons = lessons.count()
        completed_lessons = progress_records.filter(completed=True).count()
        progress_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        
        # Get learning streak
        try:
            latest_streak = LearningStreak.objects.filter(student=user).order_by('-date').first()
            current_streak = latest_streak.streak_count if latest_streak else 0
        except LearningStreak.DoesNotExist:
            current_streak = 0
        
        # Get recent downloads
        recent_downloads = LessonDownload.objects.filter(student=user).order_by('-downloaded_at')[:5]
        
        # Prepare lessons data
        lessons_data = []
        for lesson in lessons:
            lesson_data = {
                'id': lesson.id,
                'title': lesson.title,
                'description': lesson.description,
                'lesson_type': lesson.lesson_type,
                'language': lesson.get_language_display(),
                'completed': lesson.id in progress_dict and progress_dict[lesson.id].completed,
                'file_available': bool(lesson.file),
                'duration': '45 min'  # Default duration, can be made dynamic
            }
            lessons_data.append(lesson_data)
        
        # Prepare downloads data
        downloads_data = []
        for download in recent_downloads:
            downloads_data.append({
                'id': download.id,
                'lesson_title': download.lesson.title,
                'downloaded_at': download.downloaded_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Response data
        response_data = {
            'user': {
                'name': user.first_name or user.username,
                'username': user.username,
                'avatar': 'https://via.placeholder.com/80x80',
                'is_online': True
            },
            'stats': {
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'progress_percentage': round(progress_percentage, 1),
                'streak': current_streak
            },
            'lessons': lessons_data,
            'recent_downloads': downloads_data,
            'profile': {
                'grade': profile.grade if profile else 'Not set',
                'school': profile.school if profile else 'Not set',
                'language_preference': profile.language_preference if profile else 'en'
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def download_lesson(request, lesson_id):
    """
    API endpoint to download a lesson for offline use
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
        user = request.user
        
        # Create or update offline content record
        offline_content, created = LessonDownload.objects.get_or_create(
            student=user,
            lesson=lesson,
            defaults={'downloaded_at': timezone.now()}
        )
        
        if not created:
            offline_content.downloaded_at = timezone.now()
            offline_content.save()
        
        return Response({
            'message': 'Lesson downloaded successfully',
            'lesson_id': lesson_id,
            'lesson_title': lesson.title
        }, status=status.HTTP_200_OK)
        
    except Lesson.DoesNotExist:
        return Response(
            {'error': 'Lesson not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_lesson_progress(request, lesson_id):
    """
    API endpoint to update lesson progress
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
        user = request.user
        
        data = request.data
        completed = data.get('completed', False)
        score = data.get('score', 0)
        
        # Create or update progress record
        progress, created = ModuleProgress.objects.get_or_create(
            student=user,
            lesson=lesson,
            defaults={
                'completed': completed,
                'score': score,
                'completed_at': timezone.now() if completed else None
            }
        )
        
        if not created:
            progress.completed = completed
            progress.score = score
            if completed and not progress.completed_at:
                progress.completed_at = timezone.now()
            progress.save()
        
        # Update learning streak if lesson completed
        if completed:
            today = timezone.now().date()
            streak, created = LearningStreak.objects.get_or_create(
                student=user,
                date=today,
                defaults={'lessons_completed': 1, 'streak_count': 1}
            )
            
            if not created:
                streak.lessons_completed += 1
                streak.save()
            else:
                # Calculate streak count based on previous day
                yesterday = today - timezone.timedelta(days=1)
                try:
                    prev_streak = LearningStreak.objects.get(student=user, date=yesterday)
                    streak.streak_count = prev_streak.streak_count + 1
                    streak.save()
                except LearningStreak.DoesNotExist:
                    pass  # streak_count remains 1
        
        return Response({
            'message': 'Progress updated successfully',
            'lesson_id': lesson_id,
            'completed': completed,
            'score': score
        }, status=status.HTTP_200_OK)
        
    except Lesson.DoesNotExist:
        return Response(
            {'error': 'Lesson not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    API endpoint to get user profile information
    """
    try:
        user = request.user
        
        try:
            profile = UserProfile.objects.get(user=user)
            profile_data = {
                'grade': profile.grade,
                'school': profile.school,
                'language_preference': profile.language_preference,
                'date_of_birth': profile.date_of_birth.strftime('%Y-%m-%d') if profile.date_of_birth else None,
                'gender': profile.gender,
                'parent_name': profile.parent_name,
                'parent_contact': profile.parent_contact
            }
        except UserProfile.DoesNotExist:
            profile_data = {
                'grade': None,
                'school': None,
                'language_preference': 'en',
                'date_of_birth': None,
                'gender': None,
                'parent_name': None,
                'parent_contact': None
            }
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'profile': profile_data
        }
        
        return Response(user_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['POST'])
def login_api(request):
    """
    API endpoint for user login
    """
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({
                'error': 'Username and password are required'
            }, status=400)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Get user profile
            try:
                profile = UserProfile.objects.get(user=user)
                role = profile.role
            except UserProfile.DoesNotExist:
                role = 'student'  # Default role
            
            return JsonResponse({
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'role': role
                },
                'redirect_url': f'/{role}_dashboard'
            }, status=200)
        else:
            return JsonResponse({
                'error': 'Invalid username or password'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)