"""
Parent Notification Service
Handles creating, sending, and managing notifications for parents
"""
from django.utils import timezone
from django.contrib.auth.models import User
from django.template import Template, Context
from datetime import datetime, timedelta
import logging

from .models import UserProfile
from .notification_models import NotificationSettings, ParentNotification, NotificationTemplate

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing parent notifications"""
    
    @staticmethod
    def create_notification(parent, child, notification_type, lesson=None, **data):
        """Create a new notification"""
        try:
            # Get or create notification settings
            settings, created = NotificationSettings.objects.get_or_create(parent=parent)
            
            # Check if this type of notification is enabled
            if not NotificationService._should_send_notification(settings, notification_type):
                return None
            
            # Get template for this notification type
            template = NotificationService._get_template(notification_type)
            
            # Prepare template context
            context = {
                'child_name': child.first_name or child.username,
                'parent_name': parent.first_name or parent.username,
                'lesson_title': lesson.title if lesson else '',
                **data
            }
            
            # Render title and message
            title = Template(template['title']).render(Context(context))
            message = Template(template['message']).render(Context(context))
            
            # Create notification
            notification = ParentNotification.objects.create(
                parent=parent,
                child=child,
                notification_type=notification_type,
                title=title,
                message=message,
                lesson=lesson,
                data=data
            )
            
            # Send immediately if settings allow
            if settings.in_app_notifications:
                NotificationService._send_notification(notification, settings)
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    @staticmethod
    def notify_lesson_completion(child, lesson, score=None, time_spent=None):
        """Send notification when child completes a lesson"""
        parent_profile = UserProfile.objects.filter(children__user=child).first()
        if not parent_profile:
            return None
        
        parent = parent_profile.user
        data = {
            'score': score,
            'time_spent': str(time_spent) if time_spent else None,
            'lesson_type': lesson.get_lesson_type_display()
        }
        
        return NotificationService.create_notification(
            parent=parent,
            child=child,
            notification_type='lesson_complete',
            lesson=lesson,
            **data
        )
    
    @staticmethod
    def notify_quiz_passed(child, lesson, score):
        """Send notification when child passes a quiz"""
        parent_profile = UserProfile.objects.filter(children__user=child).first()
        if not parent_profile:
            return None
        
        parent = parent_profile.user
        data = {'score': score}
        
        return NotificationService.create_notification(
            parent=parent,
            child=child,
            notification_type='quiz_passed',
            lesson=lesson,
            **data
        )
    
    @staticmethod
    def notify_streak_milestone(child, streak_count):
        """Send notification when child achieves a learning streak milestone"""
        parent_profile = UserProfile.objects.filter(children__user=child).first()
        if not parent_profile:
            return None
        
        parent = parent_profile.user
        data = {'streak_count': streak_count}
        
        return NotificationService.create_notification(
            parent=parent,
            child=child,
            notification_type='streak_milestone',
            **data
        )
    
    @staticmethod
    def notify_inactivity(child, days_inactive):
        """Send notification when child has been inactive"""
        parent_profile = UserProfile.objects.filter(children__user=child).first()
        if not parent_profile:
            return None
        
        parent = parent_profile.user
        data = {'days_inactive': days_inactive}
        
        return NotificationService.create_notification(
            parent=parent,
            child=child,
            notification_type='inactivity_alert',
            **data
        )
    
    @staticmethod
    def send_weekly_summary(parent, child):
        """Send weekly progress summary"""
        from .analytics import get_progress_chart_data, get_current_streak
        
        # Get weekly data
        weekly_data = get_progress_chart_data(child, period='week')
        current_streak = get_current_streak(child)
        
        # Calculate weekly stats
        if weekly_data['lessons']:
            total_lessons = sum(weekly_data['lessons'][-1:])  # This week
            total_time = sum(weekly_data['time'][-1:])  # This week
        else:
            total_lessons = 0
            total_time = 0
        
        data = {
            'total_lessons': total_lessons,
            'total_time_hours': round(total_time, 1),
            'current_streak': current_streak
        }
        
        return NotificationService.create_notification(
            parent=parent,
            child=child,
            notification_type='weekly_summary',
            **data
        )
    
    @staticmethod
    def get_unread_notifications(parent):
        """Get all unread notifications for a parent"""
        return ParentNotification.objects.filter(
            parent=parent,
            status__in=['pending', 'sent']
        ).order_by('-created_at')
    
    @staticmethod
    def mark_all_as_read(parent):
        """Mark all notifications as read for a parent"""
        ParentNotification.objects.filter(
            parent=parent,
            status__in=['pending', 'sent']
        ).update(
            status='read',
            read_at=timezone.now()
        )
    
    @staticmethod
    def _should_send_notification(settings, notification_type):
        """Check if notification should be sent based on settings"""
        # Check quiet hours
        now = timezone.now().time()
        if settings.quiet_hours_start < settings.quiet_hours_end:
            # Normal case: 22:00 - 08:00
            if settings.quiet_hours_start <= now or now <= settings.quiet_hours_end:
                return False
        else:
            # Overnight case: 08:00 - 22:00 (quiet during day)
            if settings.quiet_hours_end <= now <= settings.quiet_hours_start:
                return False
        
        # Check notification type settings
        type_setting = getattr(settings, notification_type.replace('_', '_'), 'immediate')
        return type_setting != 'never'
    
    @staticmethod
    def _send_notification(notification, settings):
        """Actually send the notification"""
        try:
            # For now, just mark as sent (in-app notification)
            # In production, this would integrate with email/SMS services
            notification.mark_as_sent(via_app=True)
            logger.info(f"Sent notification {notification.id} to {notification.parent.username}")
            
        except Exception as e:
            notification.status = 'failed'
            notification.save()
            logger.error(f"Failed to send notification {notification.id}: {e}")
    
    @staticmethod
    def _get_template(notification_type):
        """Get notification template"""
        # Default templates
        templates = {
            'lesson_complete': {
                'title': '🎉 {{ child_name }} completed a lesson!',
                'message': '{{ child_name }} just finished "{{ lesson_title }}"{% if score %} with a score of {{ score }}%{% endif %}. Great progress!'
            },
            'quiz_passed': {
                'title': '🏆 {{ child_name }} passed a quiz!',
                'message': '{{ child_name }} scored {{ score }}% on the quiz for "{{ lesson_title }}". Excellent work!'
            },
            'streak_milestone': {
                'title': '🔥 {{ streak_count }} day learning streak!',
                'message': '{{ child_name }} has been learning consistently for {{ streak_count }} days in a row. This is fantastic dedication!'
            },
            'weekly_summary': {
                'title': '📊 Weekly Progress Report for {{ child_name }}',
                'message': 'This week {{ child_name }} completed {{ total_lessons }} lessons and spent {{ total_time_hours }} hours learning. Current streak: {{ current_streak }} days.'
            },
            'inactivity_alert': {
                'title': '⏰ {{ child_name }} hasn\'t been active',
                'message': '{{ child_name }} hasn\'t logged in for {{ days_inactive }} days. Consider encouraging them to continue their learning journey!'
            }
        }
        
        # Try to get from database first
        try:
            template_obj = NotificationTemplate.objects.get(notification_type=notification_type)
            return {
                'title': template_obj.title_template,
                'message': template_obj.message_template
            }
        except NotificationTemplate.DoesNotExist:
            return templates.get(notification_type, {
                'title': 'Learning Update for {{ child_name }}',
                'message': 'Your child has a learning update!'
            })


def create_default_notification_templates():
    """Create default notification templates"""
    templates = [
        {
            'notification_type': 'lesson_complete',
            'title_template': '🎉 {{ child_name }} completed a lesson!',
            'message_template': '{{ child_name }} just finished "{{ lesson_title }}"{% if score %} with a score of {{ score }}%{% endif %}. Great progress!'
        },
        {
            'notification_type': 'quiz_passed',
            'title_template': '🏆 {{ child_name }} passed a quiz!',
            'message_template': '{{ child_name }} scored {{ score }}% on the quiz for "{{ lesson_title }}". Excellent work!'
        },
        {
            'notification_type': 'streak_milestone',
            'title_template': '🔥 {{ streak_count }} day learning streak!',
            'message_template': '{{ child_name }} has been learning consistently for {{ streak_count }} days in a row. This is fantastic dedication!'
        },
        {
            'notification_type': 'weekly_summary',
            'title_template': '📊 Weekly Progress Report for {{ child_name }}',
            'message_template': 'This week {{ child_name }} completed {{ total_lessons }} lessons and spent {{ total_time_hours }} hours learning. Current streak: {{ current_streak }} days.'
        },
        {
            'notification_type': 'inactivity_alert',
            'title_template': '⏰ {{ child_name }} hasn\'t been active',
            'message_template': '{{ child_name }} hasn\'t logged in for {{ days_inactive }} days. Consider encouraging them to continue their learning journey!'
        }
    ]
    
    for template_data in templates:
        NotificationTemplate.objects.get_or_create(
            notification_type=template_data['notification_type'],
            defaults={
                'title_template': template_data['title_template'],
                'message_template': template_data['message_template']
            }
        )