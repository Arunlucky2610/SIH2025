"""
Parent Notification System Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class NotificationSettings(models.Model):
    """Parent notification preferences"""
    FREQUENCY_CHOICES = [
        ('immediate', 'Immediate'),
        ('daily', 'Daily Summary'),
        ('weekly', 'Weekly Summary'),
        ('never', 'Never'),
    ]
    
    parent = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='notification_settings'
    )
    
    # Notification preferences
    lesson_completion = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES, 
        default='immediate',
        help_text="When child completes a lesson"
    )
    
    streak_milestones = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES, 
        default='immediate',
        help_text="When child achieves learning streaks"
    )
    
    inactivity_alerts = models.CharField(
        max_length=20, 
        choices=FREQUENCY_CHOICES, 
        default='daily',
        help_text="When child hasn't been active"
    )
    
    weekly_summary = models.BooleanField(
        default=True,
        help_text="Weekly progress summary"
    )
    
    monthly_summary = models.BooleanField(
        default=True,
        help_text="Monthly progress report"
    )
    
    # Contact preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=True)
    
    # Timing preferences
    quiet_hours_start = models.TimeField(
        default=timezone.datetime.strptime('22:00', '%H:%M').time(),
        help_text="No notifications after this time"
    )
    quiet_hours_end = models.TimeField(
        default=timezone.datetime.strptime('08:00', '%H:%M').time(),
        help_text="No notifications before this time"
    )
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Settings for {self.parent.username}"


class ParentNotification(models.Model):
    """Individual notification records"""
    NOTIFICATION_TYPES = [
        ('lesson_complete', 'Lesson Completed'),
        ('quiz_passed', 'Quiz Passed'),
        ('streak_milestone', 'Streak Milestone'),
        ('weekly_summary', 'Weekly Summary'),
        ('monthly_summary', 'Monthly Summary'),
        ('inactivity_alert', 'Inactivity Alert'),
        ('achievement', 'Achievement Unlocked'),
        ('goal_reached', 'Goal Reached'),
        ('recommendation', 'Learning Recommendation'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ]
    
    parent = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    
    child = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='parent_notifications',
        help_text="The child this notification is about"
    )
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional lesson reference
    lesson = models.ForeignKey(
        'learning.Lesson', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    # Metadata
    data = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Additional notification data (scores, streaks, etc.)"
    )
    
    # Timing
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Delivery channels
    sent_via_email = models.BooleanField(default=False)
    sent_via_sms = models.BooleanField(default=False)
    sent_via_app = models.BooleanField(default=False)
    
    # Priority (for future use)
    priority = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High')],
        default='normal'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['parent', 'status']),
            models.Index(fields=['child', 'notification_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.child.first_name} to {self.parent.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if self.status != 'read':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save()
    
    def mark_as_sent(self, via_email=False, via_sms=False, via_app=False):
        """Mark notification as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.sent_via_email = via_email
        self.sent_via_sms = via_sms
        self.sent_via_app = via_app
        self.save()
    
    def get_status_color(self):
        """Get Bootstrap color class for status"""
        colors = {
            'pending': 'warning',
            'sent': 'info',
            'read': 'success',
            'failed': 'danger'
        }
        return colors.get(self.status, 'secondary')
    
    def get_status_display(self):
        """Get human-readable status"""
        displays = {
            'pending': 'Pending',
            'sent': 'New',
            'read': 'Read',
            'failed': 'Failed'
        }
        return displays.get(self.status, 'Unknown')


class NotificationTemplate(models.Model):
    """Templates for different notification types"""
    notification_type = models.CharField(max_length=20, unique=True)
    title_template = models.CharField(max_length=200)
    message_template = models.TextField()
    
    # Template variables that can be used:
    # {child_name}, {lesson_title}, {score}, {streak_count}, {time_spent}, etc.
    
    def __str__(self):
        return f"Template: {self.notification_type}"