from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date

# User Profile to extend Django's built-in User model
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('parent', 'Parent'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    language_preference = models.CharField(max_length=5, default='en', choices=[
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('pa', 'Punjabi'),
    ])
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='children', limit_choices_to={'role': 'parent'})
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.user.username} ({self.role})"

# Lesson model for storing learning content
class Lesson(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('pa', 'Punjabi'),
    ]
    
    LESSON_TYPE_CHOICES = [
        ('basic', 'Basic Digital Literacy'),
        ('computer', 'Computer Basics'),
        ('internet', 'Internet Basics'),
        ('mobile', 'Mobile Usage'),
        ('safety', 'Digital Safety'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    lesson_type = models.CharField(max_length=20, choices=LESSON_TYPE_CHOICES, default='basic')
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    file = models.FileField(upload_to='lessons/', null=True, blank=True)
    video_url = models.URLField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)  # For text-based lessons
    order = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lessons_created')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lesson_type', 'order', 'title']
    
    def __str__(self):
        return f"{self.title} ({self.language})"

# Track student progress on lessons
class ModuleProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='student_progress')
    completed = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)  # Quiz score if applicable
    time_spent = models.DurationField(null=True, blank=True)  # Time spent on lesson
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['student', 'lesson']
    
    def __str__(self):
        return f"{self.student.username} - {self.lesson.title} ({'Completed' if self.completed else 'In Progress'})"

# Quiz model for assessment
class Quiz(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes')
    question = models.TextField()
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ])
    explanation = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['lesson', 'order']
    
    def __str__(self):
        return f"Quiz for {self.lesson.title}: {self.question[:50]}..."

# Track quiz attempts
class QuizAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    selected_answer = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
    ])
    is_correct = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['student', 'quiz']
    
    def __str__(self):
        return f"{self.student.username} - {self.quiz.question[:30]}... ({'Correct' if self.is_correct else 'Incorrect'})"

# Download tracking for offline capability
class LessonDownload(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='downloads')
    downloaded_at = models.DateTimeField(default=timezone.now)
    file_size = models.BigIntegerField(null=True, blank=True)  # in bytes
    
    class Meta:
        unique_together = ['student', 'lesson']
    
    def __str__(self):
        return f"{self.student.username} downloaded {self.lesson.title}"

# Track user login sessions
class LoginSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_sessions')
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)  # Browser/device info
    session_key = models.CharField(max_length=40, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def session_duration(self):
        """Calculate session duration"""
        if self.logout_time:
            return self.logout_time - self.login_time
        return timezone.now() - self.login_time
    
    @property
    def is_currently_active(self):
        """Check if session is currently active"""
        return self.is_active and not self.logout_time

# Track daily learning streaks
class LearningStreak(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_streaks')
    date = models.DateField(default=timezone.now)
    lessons_completed = models.IntegerField(default=0)
    time_spent = models.DurationField(default=timezone.timedelta(minutes=0))
    streak_count = models.IntegerField(default=1)  # Current streak length
    
    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.username} - {self.date} (Streak: {self.streak_count})"

# Track weekly learning progress
class WeeklyProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_progress')
    week_start = models.DateField()  # Monday of the week
    lessons_completed = models.IntegerField(default=0)
    total_time_spent = models.DurationField(default=timezone.timedelta(minutes=0))
    average_score = models.FloatField(default=0.0)
    active_days = models.IntegerField(default=0)  # Days student was active this week
    
    class Meta:
        unique_together = ['student', 'week_start']
        ordering = ['-week_start']
    
    def __str__(self):
        return f"{self.student.username} - Week of {self.week_start}"

# Track monthly learning progress
class MonthlyProgress(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_progress')
    year = models.IntegerField()
    month = models.IntegerField()  # 1-12
    lessons_completed = models.IntegerField(default=0)
    total_time_spent = models.DurationField(default=timezone.timedelta(minutes=0))
    average_score = models.FloatField(default=0.0)
    active_days = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)  # Longest streak this month
    
    class Meta:
        unique_together = ['student', 'year', 'month']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.student.username} - {self.year}/{self.month:02d}"

# Track subject-wise performance
class SubjectPerformance(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subject_performance')
    lesson_type = models.CharField(max_length=20, choices=Lesson.LESSON_TYPE_CHOICES)
    total_lessons = models.IntegerField(default=0)
    completed_lessons = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    total_time_spent = models.DurationField(default=timezone.timedelta(minutes=0))
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'lesson_type']
    
    def __str__(self):
        return f"{self.student.username} - {self.get_lesson_type_display()}"
    
    @property
    def completion_percentage(self):
        if self.total_lessons > 0:
            return (self.completed_lessons / self.total_lessons) * 100
        return 0

# Track learning activities for calendar view
class LearningActivity(models.Model):
    ACTIVITY_TYPES = [
        ('lesson_start', 'Lesson Started'),
        ('lesson_complete', 'Lesson Completed'),
        ('quiz_attempt', 'Quiz Attempted'),
        ('quiz_passed', 'Quiz Passed'),
        ('streak_milestone', 'Streak Milestone'),
        ('weekly_goal', 'Weekly Goal Achieved'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.get_activity_type_display()}"
