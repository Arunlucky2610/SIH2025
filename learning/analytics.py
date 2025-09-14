"""
Analytics utilities for tracking student progress and generating reports for parents
"""
from django.db.models import Avg, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
from collections import defaultdict
import calendar

from .models import (ModuleProgress, LearningStreak, WeeklyProgress, MonthlyProgress, 
                    SubjectPerformance, LearningActivity, Lesson, User)


def update_learning_streak(student, lesson_completed_today=True):
    """Update learning streak for a student"""
    today = timezone.now().date()
    
    # Get or create today's streak record
    streak, created = LearningStreak.objects.get_or_create(
        student=student,
        date=today,
        defaults={
            'lessons_completed': 0,
            'time_spent': timedelta(minutes=0),
            'streak_count': 1
        }
    )
    
    if lesson_completed_today:
        streak.lessons_completed += 1
    
    # Update time spent (get from ModuleProgress for today)
    today_progress = ModuleProgress.objects.filter(
        student=student,
        started_at__date=today,
        time_spent__isnull=False
    ).aggregate(total_time=Sum('time_spent'))
    
    streak.time_spent = today_progress['total_time'] or timedelta(minutes=0)
    
    # Calculate streak count
    if created or streak.lessons_completed == 1:
        # Check yesterday's streak
        yesterday = today - timedelta(days=1)
        try:
            yesterday_streak = LearningStreak.objects.get(student=student, date=yesterday)
            streak.streak_count = yesterday_streak.streak_count + 1
        except LearningStreak.DoesNotExist:
            streak.streak_count = 1
    
    streak.save()
    return streak


def update_weekly_progress(student, week_start=None):
    """Update weekly progress for a student"""
    if not week_start:
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())  # Get Monday
    
    week_end = week_start + timedelta(days=6)
    
    # Get or create weekly progress record
    weekly, created = WeeklyProgress.objects.get_or_create(
        student=student,
        week_start=week_start,
        defaults={
            'lessons_completed': 0,
            'total_time_spent': timedelta(minutes=0),
            'average_score': 0.0,
            'active_days': 0
        }
    )
    
    # Get all progress for this week
    week_progress = ModuleProgress.objects.filter(
        student=student,
        started_at__date__range=[week_start, week_end]
    )
    
    # Update statistics
    weekly.lessons_completed = week_progress.filter(completed=True).count()
    
    # Calculate total time spent
    time_data = week_progress.filter(time_spent__isnull=False).aggregate(
        total_time=Sum('time_spent')
    )
    weekly.total_time_spent = time_data['total_time'] or timedelta(minutes=0)
    
    # Calculate average score
    score_data = week_progress.filter(score__isnull=False).aggregate(
        avg_score=Avg('score')
    )
    weekly.average_score = score_data['avg_score'] or 0.0
    
    # Count active days
    active_dates = week_progress.values_list('started_at__date', flat=True).distinct()
    weekly.active_days = len(set(active_dates))
    
    weekly.save()
    return weekly


def update_monthly_progress(student, year=None, month=None):
    """Update monthly progress for a student"""
    if not year or not month:
        today = timezone.now().date()
        year, month = today.year, today.month
    
    # Get month boundaries
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    # Get or create monthly progress record
    monthly, created = MonthlyProgress.objects.get_or_create(
        student=student,
        year=year,
        month=month,
        defaults={
            'lessons_completed': 0,
            'total_time_spent': timedelta(minutes=0),
            'average_score': 0.0,
            'active_days': 0,
            'max_streak': 0
        }
    )
    
    # Get all progress for this month
    month_progress = ModuleProgress.objects.filter(
        student=student,
        started_at__date__range=[month_start, month_end]
    )
    
    # Update statistics
    monthly.lessons_completed = month_progress.filter(completed=True).count()
    
    # Calculate total time spent
    time_data = month_progress.filter(time_spent__isnull=False).aggregate(
        total_time=Sum('time_spent')
    )
    monthly.total_time_spent = time_data['total_time'] or timedelta(minutes=0)
    
    # Calculate average score
    score_data = month_progress.filter(score__isnull=False).aggregate(
        avg_score=Avg('score')
    )
    monthly.average_score = score_data['avg_score'] or 0.0
    
    # Count active days
    active_dates = month_progress.values_list('started_at__date', flat=True).distinct()
    monthly.active_days = len(set(active_dates))
    
    # Find max streak for this month
    month_streaks = LearningStreak.objects.filter(
        student=student,
        date__range=[month_start, month_end]
    ).order_by('-streak_count')
    
    if month_streaks:
        monthly.max_streak = month_streaks.first().streak_count
    
    monthly.save()
    return monthly


def update_subject_performance(student, lesson_type=None):
    """Update subject-wise performance for a student"""
    if lesson_type:
        lesson_types = [lesson_type]
    else:
        lesson_types = [choice[0] for choice in Lesson.LESSON_TYPE_CHOICES]
    
    for ltype in lesson_types:
        # Get or create subject performance record
        subject_perf, created = SubjectPerformance.objects.get_or_create(
            student=student,
            lesson_type=ltype,
            defaults={
                'total_lessons': 0,
                'completed_lessons': 0,
                'average_score': 0.0,
                'total_time_spent': timedelta(minutes=0)
            }
        )
        
        # Get all lessons of this type
        type_lessons = Lesson.objects.filter(lesson_type=ltype, is_active=True)
        subject_perf.total_lessons = type_lessons.count()
        
        # Get student progress for this lesson type
        type_progress = ModuleProgress.objects.filter(
            student=student,
            lesson__lesson_type=ltype
        )
        
        subject_perf.completed_lessons = type_progress.filter(completed=True).count()
        
        # Calculate average score
        score_data = type_progress.filter(score__isnull=False).aggregate(
            avg_score=Avg('score')
        )
        subject_perf.average_score = score_data['avg_score'] or 0.0
        
        # Calculate total time spent
        time_data = type_progress.filter(time_spent__isnull=False).aggregate(
            total_time=Sum('time_spent')
        )
        subject_perf.total_time_spent = time_data['total_time'] or timedelta(minutes=0)
        
        subject_perf.save()


def log_learning_activity(student, activity_type, lesson=None, description=""):
    """Log a learning activity for timeline/calendar view"""
    LearningActivity.objects.create(
        student=student,
        activity_type=activity_type,
        lesson=lesson,
        description=description
    )


def get_progress_chart_data(student, period='month'):
    """Get data for progress charts"""
    if period == 'week':
        # Get last 8 weeks
        end_date = timezone.now().date()
        start_date = end_date - timedelta(weeks=8)
        
        weekly_data = WeeklyProgress.objects.filter(
            student=student,
            week_start__gte=start_date
        ).order_by('week_start')
        
        return {
            'labels': [f"Week of {w.week_start.strftime('%m/%d')}" for w in weekly_data],
            'lessons': [w.lessons_completed for w in weekly_data],
            'time': [w.total_time_spent.total_seconds() / 3600 for w in weekly_data],  # hours
            'scores': [w.average_score for w in weekly_data]
        }
    
    elif period == 'month':
        # Get last 6 months
        monthly_data = MonthlyProgress.objects.filter(
            student=student
        ).order_by('-year', '-month')[:6]
        
        monthly_data = list(reversed(monthly_data))  # Chronological order
        
        return {
            'labels': [f"{m.year}/{m.month:02d}" for m in monthly_data],
            'lessons': [m.lessons_completed for m in monthly_data],
            'time': [m.total_time_spent.total_seconds() / 3600 for m in monthly_data],  # hours
            'scores': [m.average_score for m in monthly_data],
            'streaks': [m.max_streak for m in monthly_data]
        }


def get_subject_performance_data(student):
    """Get subject-wise performance data"""
    subject_data = SubjectPerformance.objects.filter(student=student)
    
    return {
        'subjects': [s.get_lesson_type_display() for s in subject_data],
        'completion': [s.completion_percentage for s in subject_data],
        'scores': [s.average_score for s in subject_data],
        'time': [s.total_time_spent.total_seconds() / 3600 for s in subject_data]  # hours
    }


def get_learning_calendar_data(student, year, month):
    """Get learning activity data for calendar view"""
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    
    activities = LearningActivity.objects.filter(
        student=student,
        created_at__date__range=[month_start, month_end]
    ).order_by('created_at')
    
    # Group activities by date
    calendar_data = defaultdict(list)
    for activity in activities:
        day = activity.created_at.date().day
        calendar_data[day].append({
            'type': activity.activity_type,
            'description': activity.description,
            'time': activity.created_at.strftime('%H:%M'),
            'lesson': activity.lesson.title if activity.lesson else None
        })
    
    return dict(calendar_data)


def get_current_streak(student):
    """Get current learning streak for a student"""
    today = timezone.now().date()
    try:
        latest_streak = LearningStreak.objects.filter(
            student=student,
            date__lte=today
        ).latest('date')
        
        # Check if streak is current (within last 2 days)
        if (today - latest_streak.date).days <= 1:
            return latest_streak.streak_count
        else:
            return 0
    except LearningStreak.DoesNotExist:
        return 0


def update_all_analytics_for_student(student):
    """Update all analytics for a student - useful for batch updates"""
    # Update current week and month
    update_weekly_progress(student)
    update_monthly_progress(student)
    update_subject_performance(student)
    
    # Update learning streak if they've been active today
    today_progress = ModuleProgress.objects.filter(
        student=student,
        started_at__date=timezone.now().date()
    ).exists()
    
    if today_progress:
        update_learning_streak(student, lesson_completed_today=True)