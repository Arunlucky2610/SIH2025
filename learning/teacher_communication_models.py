"""
Teacher Communication Models
Models for handling communication between parents and teachers
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .models import UserProfile, Lesson

class TeacherAssignment(models.Model):
    """Maps teachers to their subjects and classes"""
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, 
                              limit_choices_to={'userprofile__role': 'teacher'},
                              related_name='teacher_assignments')
    subject = models.CharField(max_length=20, choices=Lesson.LESSON_TYPE_CHOICES)
    class_name = models.CharField(max_length=50, help_text="e.g., 'Grade 5A', 'Beginner Digital Literacy'")
    is_class_teacher = models.BooleanField(default=False, help_text="Is this teacher the main class teacher?")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['teacher', 'subject', 'class_name']
    
    def __str__(self):
        role = "Class Teacher" if self.is_class_teacher else "Subject Teacher"
        return f"{self.teacher.get_full_name() or self.teacher.username} - {self.get_subject_display()} ({role})"

class TeacherMessage(models.Model):
    """Messages between parents and teachers"""
    MESSAGE_TYPES = [
        ('inquiry', 'General Inquiry'),
        ('progress', 'Progress Discussion'),
        ('behavior', 'Behavior Discussion'),
        ('homework', 'Homework/Assignment'),
        ('attendance', 'Attendance Issue'),
        ('suggestion', 'Suggestion/Feedback'),
        ('meeting', 'Meeting Request'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('resolved', 'Resolved'),
    ]
    
    # Message details
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_teacher_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_teacher_messages')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussed_messages',
                               limit_choices_to={'userprofile__role': 'student'},
                               help_text="The student this message is about")
    
    # Message content
    subject = models.CharField(max_length=200)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='inquiry')
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Message status
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Parent message reference (for threading)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='replies')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username}: {self.subject}"
    
    @property
    def is_from_parent(self):
        try:
            return self.sender.userprofile.role == 'parent'
        except:
            return False
    
    @property
    def is_from_teacher(self):
        try:
            return self.sender.userprofile.role == 'teacher'
        except:
            return False
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.status = 'read'
            self.save()

class TeacherAvailability(models.Model):
    """Teacher availability for communication"""
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    teacher = models.ForeignKey(User, on_delete=models.CASCADE,
                              limit_choices_to={'userprofile__role': 'teacher'},
                              related_name='availability_schedule')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Special notes about availability")
    
    class Meta:
        unique_together = ['teacher', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.teacher.username} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

class ConversationThread(models.Model):
    """Group related messages into conversation threads"""
    participants = models.ManyToManyField(User, related_name='conversation_threads')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_threads_about',
                               limit_choices_to={'userprofile__role': 'student'})
    subject = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-last_message_at']
    
    def __str__(self):
        participant_names = ", ".join([p.username for p in self.participants.all()[:3]])
        return f"Conversation about {self.student.username}: {self.subject}"
    
    @property
    def unread_count_for_user(self, user):
        """Get unread message count for a specific user"""
        return TeacherMessage.objects.filter(
            parent_message__isnull=True,  # Only count main messages, not replies
            recipient=user,
            is_read=False
        ).count()

class TeacherProfile(models.Model):
    """Extended profile for teachers with communication preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                               limit_choices_to={'userprofile__role': 'teacher'},
                               related_name='teacher_profile')
    bio = models.TextField(blank=True, help_text="Brief introduction for parents")
    specialization = models.CharField(max_length=100, blank=True, 
                                    help_text="Teaching specialization/expertise")
    years_experience = models.PositiveIntegerField(default=0)
    
    # Communication preferences
    allow_parent_messages = models.BooleanField(default=True)
    response_time_hours = models.PositiveIntegerField(default=24, 
                                                    help_text="Expected response time in hours")
    preferred_contact_time = models.CharField(max_length=100, blank=True,
                                            help_text="e.g., 'Weekdays 9AM-5PM'")
    
    # Contact information
    office_location = models.CharField(max_length=100, blank=True)
    office_hours = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Teacher Profile: {self.user.get_full_name() or self.user.username}"
    
    @property
    def subjects_taught(self):
        """Get list of subjects this teacher teaches"""
        return TeacherAssignment.objects.filter(teacher=self.user, is_active=True)
    
    @property
    def is_class_teacher(self):
        """Check if this teacher is a class teacher"""
        return TeacherAssignment.objects.filter(
            teacher=self.user, 
            is_class_teacher=True, 
            is_active=True
        ).exists()