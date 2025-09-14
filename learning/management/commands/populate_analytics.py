"""
Management command to populate sample analytics data for testing the enhanced parent dashboard
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta, date
import random

from learning.models import (
    ModuleProgress, UserProfile, Lesson, LearningStreak, 
    WeeklyProgress, MonthlyProgress, SubjectPerformance, LearningActivity
)


class Command(BaseCommand):
    help = 'Populate sample analytics data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Populating sample analytics data...')
        
        # Get all students
        students = User.objects.filter(userprofile__role='student')
        
        if not students.exists():
            self.stdout.write(self.style.WARNING('No students found. Please run populate_data first.'))
            return
        
        for student in students:
            self.create_analytics_for_student(student)
        
        self.stdout.write(self.style.SUCCESS('Successfully populated analytics data!'))
    
    def create_analytics_for_student(self, student):
        """Create comprehensive analytics data for a student"""
        self.stdout.write(f'Creating analytics for {student.username}...')
        
        # Create learning streaks for the past 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        current_streak = 0
        for i in range(30):
            date_to_create = start_date + timedelta(days=i)
            
            # 70% chance of learning activity on any given day
            if random.random() < 0.7:
                current_streak += 1
                lessons_completed = random.randint(1, 3)
                time_spent = timedelta(minutes=random.randint(15, 90))
                
                LearningStreak.objects.get_or_create(
                    student=student,
                    date=date_to_create,
                    defaults={
                        'lessons_completed': lessons_completed,
                        'time_spent': time_spent,
                        'streak_count': current_streak
                    }
                )
            else:
                current_streak = 0
        
        # Create weekly progress for the past 8 weeks
        for week_offset in range(8):
            week_start = end_date - timedelta(days=end_date.weekday()) - timedelta(weeks=week_offset)
            
            WeeklyProgress.objects.get_or_create(
                student=student,
                week_start=week_start,
                defaults={
                    'lessons_completed': random.randint(3, 12),
                    'total_time_spent': timedelta(hours=random.randint(2, 8)),
                    'average_score': random.uniform(60, 95),
                    'active_days': random.randint(3, 7)
                }
            )
        
        # Create monthly progress for the past 6 months
        for month_offset in range(6):
            target_date = end_date - timedelta(days=30 * month_offset)
            year, month = target_date.year, target_date.month
            
            MonthlyProgress.objects.get_or_create(
                student=student,
                year=year,
                month=month,
                defaults={
                    'lessons_completed': random.randint(8, 25),
                    'total_time_spent': timedelta(hours=random.randint(10, 30)),
                    'average_score': random.uniform(65, 90),
                    'active_days': random.randint(15, 28),
                    'max_streak': random.randint(3, 14)
                }
            )
        
        # Create subject performance data
        for lesson_type, _ in Lesson.LESSON_TYPE_CHOICES:
            total_lessons = random.randint(5, 15)
            completed_lessons = random.randint(1, total_lessons)
            
            SubjectPerformance.objects.get_or_create(
                student=student,
                lesson_type=lesson_type,
                defaults={
                    'total_lessons': total_lessons,
                    'completed_lessons': completed_lessons,
                    'average_score': random.uniform(60, 95),
                    'total_time_spent': timedelta(hours=random.randint(2, 10))
                }
            )
        
        # Create learning activities for the past 2 weeks
        activity_types = ['lesson_start', 'lesson_complete', 'quiz_attempt', 'quiz_passed']
        lessons = Lesson.objects.filter(is_active=True)[:10]
        
        for day_offset in range(14):
            activity_date = end_date - timedelta(days=day_offset)
            
            # Create 1-3 activities per day (if active)
            if random.random() < 0.7:  # 70% chance of activity
                num_activities = random.randint(1, 3)
                
                for _ in range(num_activities):
                    activity_type = random.choice(activity_types)
                    lesson = random.choice(lessons) if lessons else None
                    
                    created_at = timezone.make_aware(
                        datetime.combine(
                            activity_date, 
                            datetime.min.time().replace(
                                hour=random.randint(9, 18),
                                minute=random.randint(0, 59)
                            )
                        )
                    )
                    
                    description = self.get_activity_description(activity_type, lesson)
                    
                    LearningActivity.objects.create(
                        student=student,
                        activity_type=activity_type,
                        lesson=lesson,
                        description=description,
                        created_at=created_at
                    )
    
    def get_activity_description(self, activity_type, lesson):
        """Generate description for learning activity"""
        if lesson:
            if activity_type == 'lesson_start':
                return f"Started lesson: {lesson.title}"
            elif activity_type == 'lesson_complete':
                return f"Completed lesson: {lesson.title}"
            elif activity_type == 'quiz_attempt':
                return f"Attempted quiz for: {lesson.title}"
            elif activity_type == 'quiz_passed':
                return f"Passed quiz for: {lesson.title}"
        
        return f"Learning activity: {activity_type.replace('_', ' ').title()}"