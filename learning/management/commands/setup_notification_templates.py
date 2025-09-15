"""
Management command to create default notification templates
"""
from django.core.management.base import BaseCommand

from learning.notifications import create_default_notification_templates


class Command(BaseCommand):
    help = 'Create default notification templates'

    def handle(self, *args, **options):
        self.stdout.write("Creating default notification templates...")
        
        try:
            create_default_notification_templates()
            self.stdout.write(
                self.style.SUCCESS("Successfully created default notification templates!")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error creating templates: {e}")
            )