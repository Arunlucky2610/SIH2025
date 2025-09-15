"""
Django signals to automatically update analytics when students interact with lessons
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ModuleProgress, QuizAttempt
from .analytics import (
    update_learning_streak, update_weekly_progress, update_monthly_progress,
    update_subject_performance, log_learning_activity
)
from .notifications import NotificationService


@receiver(post_save, sender=ModuleProgress)
def update_analytics_on_progress(sender, instance, created, **kwargs):
    """Update all analytics when a student's progress changes"""
    
    # If this is a new progress record (lesson started)
    if created:
        log_learning_activity(
            student=instance.student,
            activity_type='lesson_start',
            lesson=instance.lesson,
            description=f"Started lesson: {instance.lesson.title}"
        )
    
    # If lesson was just completed
    if instance.completed and hasattr(instance, '_was_completed') and not instance._was_completed:
        # Log lesson completion
        log_learning_activity(
            student=instance.student,
            activity_type='lesson_complete',
            lesson=instance.lesson,
            description=f"Completed lesson: {instance.lesson.title}"
        )
        
        # Send notification to parent
        NotificationService.notify_lesson_completion(
            child=instance.student,
            lesson=instance.lesson,
            time_spent=instance.time_spent
        )
        
        # Update learning streak (lesson completed today)
        update_learning_streak(instance.student, lesson_completed_today=True)
        
        # Check for streak milestones
        from .analytics import get_current_streak
        current_streak = get_current_streak(instance.student)
        if current_streak in [7, 14, 30, 60]:  # Milestone days
            log_learning_activity(
                student=instance.student,
                activity_type='streak_milestone',
                description=f"Achieved {current_streak} day learning streak!"
            )
            
            # Send streak milestone notification
            NotificationService.notify_streak_milestone(
                child=instance.student,
                streak_count=current_streak
            )
    
    # Update weekly and monthly progress
    update_weekly_progress(instance.student)
    update_monthly_progress(instance.student)
    
    # Update subject-specific performance
    update_subject_performance(instance.student, instance.lesson.lesson_type)


@receiver(pre_save, sender=ModuleProgress)
def track_completion_change(sender, instance, **kwargs):
    """Track if completion status is changing"""
    if instance.pk:
        try:
            old_instance = ModuleProgress.objects.get(pk=instance.pk)
            instance._was_completed = old_instance.completed
        except ModuleProgress.DoesNotExist:
            instance._was_completed = False
    else:
        instance._was_completed = False


@receiver(post_save, sender=QuizAttempt)
def update_analytics_on_quiz(sender, instance, created, **kwargs):
    """Update analytics when a student attempts a quiz"""
    
    if created:
        # Log quiz attempt
        log_learning_activity(
            student=instance.student,
            activity_type='quiz_attempt',
            lesson=instance.quiz.lesson,
            description=f"Attempted quiz for: {instance.quiz.lesson.title}"
        )
        
        # If quiz was passed (assuming 60% is passing)
        if instance.is_correct:
            log_learning_activity(
                student=instance.student,
                activity_type='quiz_passed',
                lesson=instance.quiz.lesson,
                description=f"Passed quiz for: {instance.quiz.lesson.title}"
            )
            
            # Send quiz passed notification
            NotificationService.notify_quiz_passed(
                child=instance.student,
                lesson=instance.quiz.lesson,
                score=85  # Default score for passing (can be calculated)
            )
    
    # Update analytics
    update_weekly_progress(instance.student)
    update_monthly_progress(instance.student)
    update_subject_performance(instance.student, instance.quiz.lesson.lesson_type)