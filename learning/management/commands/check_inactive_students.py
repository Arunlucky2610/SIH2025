"""
Management command to check for inactive students and send notifications to parents
Run this as a daily cron job
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta

from learning.models import UserProfile, ModuleProgress
from learning.notifications import NotificationService


class Command(BaseCommand):
    help = 'Check for inactive students and send notifications to parents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=3,
            help='Number of days of inactivity before sending notification (default: 3)'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        
        self.stdout.write(f"Checking for students inactive for {days_threshold} days...")
        
        # Get all student profiles
        student_profiles = UserProfile.objects.filter(role='student')
        notifications_sent = 0
        
        for profile in student_profiles:
            student = profile.user
            
            # Check if student has been active recently
            recent_activity = ModuleProgress.objects.filter(
                student=student,
                last_accessed__gte=cutoff_date
            ).exists()
            
            if not recent_activity:
                # Student has been inactive, send notification to parent
                try:
                    # Calculate exact days inactive
                    last_activity = ModuleProgress.objects.filter(
                        student=student
                    ).order_by('-last_accessed').first()
                    
                    if last_activity:
                        days_inactive = (timezone.now() - last_activity.last_accessed).days
                    else:
                        days_inactive = "many"  # No activity recorded
                    
                    # Send notification
                    notification = NotificationService.notify_inactivity(
                        child=student,
                        days_inactive=days_inactive
                    )
                    
                    if notification:
                        notifications_sent += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Sent inactivity notification for {student.username} "
                                f"({days_inactive} days inactive)"
                            )
                        )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing {student.username}: {e}"
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Inactivity check complete. Sent {notifications_sent} notifications."
            )
        )