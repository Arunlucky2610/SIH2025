"""
Management command to test notification system by creating sample notifications
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from learning.notifications import NotificationService
from learning.models import UserProfile, Lesson


class Command(BaseCommand):
    help = 'Create sample notifications to test the notification system'

    def handle(self, *args, **options):
        self.stdout.write("Creating sample notifications...")
        
        try:
            # Get a parent and child for testing
            parent_profile = UserProfile.objects.filter(role='parent').first()
            if not parent_profile:
                self.stdout.write(
                    self.style.ERROR("No parent profiles found. Please create a parent user first.")
                )
                return
            
            parent = parent_profile.user
            
            # Get a child for this parent
            child_profile = parent_profile.children.first()
            if not child_profile:
                self.stdout.write(
                    self.style.ERROR(f"No children found for parent {parent.username}")
                )
                return
            
            child = child_profile.user
            
            # Get a lesson for testing
            lesson = Lesson.objects.first()
            if not lesson:
                self.stdout.write(
                    self.style.ERROR("No lessons found. Please create lessons first.")
                )
                return
            
            # Create different types of notifications
            notifications_created = 0
            
            # 1. Lesson completion notification
            notification = NotificationService.notify_lesson_completion(
                child=child,
                lesson=lesson,
                score=85,
                time_spent=25  # minutes
            )
            if notification:
                notifications_created += 1
                self.stdout.write(f"✓ Created lesson completion notification")
            
            # 2. Quiz passed notification
            notification = NotificationService.notify_quiz_passed(
                child=child,
                lesson=lesson,
                score=92
            )
            if notification:
                notifications_created += 1
                self.stdout.write(f"✓ Created quiz passed notification")
            
            # 3. Streak milestone notification
            notification = NotificationService.notify_streak_milestone(
                child=child,
                streak_count=7
            )
            if notification:
                notifications_created += 1
                self.stdout.write(f"✓ Created streak milestone notification")
            
            # 4. Weekly summary notification
            notification = NotificationService.send_weekly_summary(
                parent=parent,
                child=child
            )
            if notification:
                notifications_created += 1
                self.stdout.write(f"✓ Created weekly summary notification")
            
            # 5. Inactivity alert notification
            notification = NotificationService.notify_inactivity(
                child=child,
                days_inactive=3
            )
            if notification:
                notifications_created += 1
                self.stdout.write(f"✓ Created inactivity alert notification")
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {notifications_created} test notifications for {parent.username}!"
                )
            )
            
            # Show notification count
            from learning.notifications import NotificationService
            unread_count = NotificationService.get_unread_notifications(parent).count()
            self.stdout.write(f"Total unread notifications for {parent.username}: {unread_count}")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating notifications: {e}")
            )