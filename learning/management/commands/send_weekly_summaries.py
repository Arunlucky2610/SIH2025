"""
Management command to send weekly progress summaries to parents
Run this weekly (e.g., every Sunday)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

from learning.models import UserProfile
from learning.notifications import NotificationService


class Command(BaseCommand):
    help = 'Send weekly progress summaries to all parents'

    def handle(self, *args, **options):
        self.stdout.write("Sending weekly progress summaries...")
        
        # Get all parent profiles
        parent_profiles = UserProfile.objects.filter(role='parent')
        summaries_sent = 0
        
        for parent_profile in parent_profiles:
            parent = parent_profile.user
            
            # Get all children for this parent
            children = parent_profile.children.all()
            
            for child_profile in children:
                child = child_profile.user
                
                try:
                    # Send weekly summary
                    notification = NotificationService.send_weekly_summary(
                        parent=parent,
                        child=child
                    )
                    
                    if notification:
                        summaries_sent += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Sent weekly summary for {child.username} to {parent.username}"
                            )
                        )
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error sending summary for {child.username}: {e}"
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Weekly summaries complete. Sent {summaries_sent} summaries."
            )
        )