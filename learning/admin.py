from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import (UserProfile, Lesson, ModuleProgress, Quiz, QuizAttempt, 
                     LessonDownload, LoginSession, LearningStreak, WeeklyProgress, 
                     MonthlyProgress, SubjectPerformance, LearningActivity,
                     Student, Parent, Teacher)
from .teacher_communication_models import (
    TeacherAssignment, TeacherMessage, TeacherAvailability,
    ConversationThread, TeacherProfile
)

# Customize admin site header and title
admin.site.site_header = "Rural Digital Learning - Admin Panel"
admin.site.site_title = "Rural Digital Learning Admin"
admin.site.index_title = "Welcome to Rural Digital Learning Administration"

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('role', 'language_preference', 'phone_number', 'parent')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'date_joined', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'userprofile__role', 'userprofile__language_preference')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    actions = ['activate_users', 'deactivate_users', 'reset_passwords']
    
    def get_role(self, obj):
        try:
            return obj.userprofile.role.title()
        except UserProfile.DoesNotExist:
            return "No Profile"
    get_role.short_description = 'Role'
    get_role.admin_order_field = 'userprofile__role'
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} user(s)")
    activate_users.short_description = "Activate selected users"
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} user(s)")
    deactivate_users.short_description = "Deactivate selected users"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('userprofile')

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'language_preference', 'phone_number', 'has_parent', 'created_at', 'user_status']
    list_filter = ['role', 'language_preference', 'created_at', 'user__is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone_number']
    list_editable = ['role', 'language_preference']
    raw_id_fields = ['parent']
    actions = ['change_to_student', 'change_to_teacher', 'change_to_parent']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role')
        }),
        ('Profile Details', {
            'fields': ('language_preference', 'phone_number', 'parent')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at']
    
    def has_parent(self, obj):
        return "✅" if obj.parent else "❌"
    has_parent.short_description = 'Has Parent'
    has_parent.boolean = True
    
    def user_status(self, obj):
        return "✅ Active" if obj.user.is_active else "❌ Inactive"
    user_status.short_description = 'Status'
    
    def change_to_student(self, request, queryset):
        updated = queryset.update(role='student')
        self.message_user(request, f"Changed {updated} profile(s) to Student")
    change_to_student.short_description = "Change role to Student"
    
    def change_to_teacher(self, request, queryset):
        updated = queryset.update(role='teacher')
        self.message_user(request, f"Changed {updated} profile(s) to Teacher")
    change_to_teacher.short_description = "Change role to Teacher"
    
    def change_to_parent(self, request, queryset):
        updated = queryset.update(role='parent')
        self.message_user(request, f"Changed {updated} profile(s) to Parent")
    change_to_parent.short_description = "Change role to Parent"

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'lesson_type', 'language', 'order', 'is_active', 'created_by', 'created_at', 'has_file', 'has_video']
    list_filter = ['lesson_type', 'language', 'is_active', 'created_at', 'created_by']
    search_fields = ['title', 'description', 'content']
    ordering = ['lesson_type', 'order', 'title']
    list_editable = ['order', 'is_active']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'lesson_type', 'language', 'order', 'is_active')
        }),
        ('Content', {
            'fields': ('content', 'file', 'video_url'),
            'description': 'Add lesson content through text, file upload, or video URL'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['duplicate_lesson', 'activate_lessons', 'deactivate_lessons', 'bulk_create_lessons']
    
    def has_file(self, obj):
        return "✅" if obj.file else "❌"
    has_file.short_description = 'File'
    has_file.boolean = True
    
    def has_video(self, obj):
        return "✅" if obj.video_url else "❌"
    has_video.short_description = 'Video'
    has_video.boolean = True
    
    def duplicate_lesson(self, request, queryset):
        for lesson in queryset:
            lesson.pk = None
            lesson.title = f"{lesson.title} (Copy)"
            lesson.created_by = request.user
            lesson.save()
        self.message_user(request, f"Duplicated {queryset.count()} lesson(s)")
    duplicate_lesson.short_description = "Duplicate selected lessons"
    
    def activate_lessons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} lesson(s)")
    activate_lessons.short_description = "Activate selected lessons"
    
    def deactivate_lessons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} lesson(s)")
    deactivate_lessons.short_description = "Deactivate selected lessons"
    
    def bulk_create_lessons(self, request, queryset):
        # Create sample lessons for demonstration
        sample_lessons = [
            {
                'title': 'Introduction to Computers',
                'description': 'Learn the basics of computer hardware and software',
                'lesson_type': 'computer',
                'language': 'en',
                'content': 'This lesson covers the fundamental concepts of computers...'
            },
            {
                'title': 'Internet Safety',
                'description': 'Learn how to stay safe online',
                'lesson_type': 'safety',
                'language': 'en',
                'content': 'Online safety is crucial in today\'s digital world...'
            },
            {
                'title': 'Mobile Phone Basics',
                'description': 'Learn how to use smartphones effectively',
                'lesson_type': 'mobile',
                'language': 'hi',
                'content': 'स्मार्टफोन का उपयोग करना सीखें...'
            }
        ]
        
        created_count = 0
        for lesson_data in sample_lessons:
            if not Lesson.objects.filter(title=lesson_data['title']).exists():
                Lesson.objects.create(
                    created_by=request.user,
                    order=Lesson.objects.count() + 1,
                    **lesson_data
                )
                created_count += 1
        
        self.message_user(request, f"Created {created_count} new sample lessons")
    bulk_create_lessons.short_description = "Create sample lessons"
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new lesson
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ModuleProgress)
class ModuleProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'completed', 'score', 'progress_status', 'time_spent_display', 'started_at', 'completed_at']
    list_filter = ['completed', 'lesson__lesson_type', 'lesson__language', 'started_at']
    search_fields = ['student__username', 'lesson__title', 'student__first_name', 'student__last_name']
    readonly_fields = ['started_at']
    actions = ['mark_completed', 'reset_progress']
    date_hierarchy = 'started_at'
    
    def progress_status(self, obj):
        if obj.completed:
            return format_html('<span style="color: green;">✅ Completed</span>')
        else:
            return format_html('<span style="color: orange;">🔄 In Progress</span>')
    progress_status.short_description = 'Status'
    
    def time_spent_display(self, obj):
        if obj.time_spent:
            total_seconds = int(obj.time_spent.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "N/A"
    time_spent_display.short_description = 'Time Spent'
    
    def mark_completed(self, request, queryset):
        updated = queryset.update(completed=True, completed_at=timezone.now())
        self.message_user(request, f"Marked {updated} progress record(s) as completed")
    mark_completed.short_description = "Mark as completed"
    
    def reset_progress(self, request, queryset):
        updated = queryset.update(completed=False, completed_at=None, score=None)
        self.message_user(request, f"Reset {updated} progress record(s)")
    reset_progress.short_description = "Reset progress"

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['lesson', 'question_preview', 'correct_answer', 'order', 'created_at']
    list_filter = ['lesson__lesson_type', 'correct_answer', 'created_at']
    search_fields = ['question', 'lesson__title']
    ordering = ['lesson', 'order']
    
    def question_preview(self, obj):
        return obj.question[:50] + "..." if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz_preview', 'selected_answer', 'is_correct', 'attempted_at']
    list_filter = ['is_correct', 'selected_answer', 'attempted_at']
    search_fields = ['student__username', 'quiz__question']
    readonly_fields = ['attempted_at']
    
    def quiz_preview(self, obj):
        return obj.quiz.question[:30] + "..." if len(obj.quiz.question) > 30 else obj.quiz.question
    quiz_preview.short_description = 'Quiz Question'

@admin.register(LessonDownload)
class LessonDownloadAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson', 'downloaded_at', 'file_size_mb']
    list_filter = ['downloaded_at', 'lesson__lesson_type']
    search_fields = ['student__username', 'lesson__title']
    readonly_fields = ['downloaded_at']
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "N/A"
    file_size_mb.short_description = 'File Size'

@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'logout_time', 'session_duration_display', 'ip_address', 'is_active_display', 'user_role', 'device_info']
    list_filter = ['is_active', 'login_time', 'user__userprofile__role']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'ip_address', 'user_agent']
    readonly_fields = ['login_time', 'session_key', 'session_duration_display', 'user_agent_display']
    date_hierarchy = 'login_time'
    actions = ['end_sessions', 'export_login_data']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'login_time', 'logout_time', 'is_active')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'session_key', 'user_agent_display'),
            'classes': ('collapse',)
        }),
    )
    
    def session_duration_display(self, obj):
        duration = obj.session_duration
        if duration:
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
        return "N/A"
    session_duration_display.short_description = 'Duration'
    
    def is_active_display(self, obj):
        if obj.is_currently_active:
            return format_html('<span style="color: green;">✅ Active</span>')
        else:
            return format_html('<span style="color: red;">❌ Ended</span>')
    is_active_display.short_description = 'Status'
    
    def user_role(self, obj):
        try:
            role = obj.user.userprofile.role.title()
            colors = {'Student': 'blue', 'Teacher': 'green', 'Parent': 'orange'}
            color = colors.get(role, 'black')
            return format_html(f'<span style="color: {color};">{role}</span>')
        except:
            return "Unknown"
    user_role.short_description = 'Role'
    
    def device_info(self, obj):
        if obj.user_agent:
            if 'Mobile' in obj.user_agent:
                return "📱 Mobile"
            elif 'Tablet' in obj.user_agent:
                return "📱 Tablet"
            else:
                return "💻 Desktop"
        return "❓ Unknown"
    device_info.short_description = 'Device'
    
    def user_agent_display(self, obj):
        return obj.user_agent[:100] + "..." if len(obj.user_agent or "") > 100 else obj.user_agent
    user_agent_display.short_description = 'User Agent'
    
    def end_sessions(self, request, queryset):
        updated = queryset.filter(is_active=True).update(
            is_active=False, 
            logout_time=timezone.now()
        )
        self.message_user(request, f"Ended {updated} active session(s)")
    end_sessions.short_description = "End selected sessions"

@admin.register(LearningStreak)
class LearningStreakAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'lessons_completed', 'time_spent', 'streak_count']
    list_filter = ['date', 'streak_count']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']
    date_hierarchy = 'date'
    readonly_fields = ['streak_count']

@admin.register(WeeklyProgress)
class WeeklyProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'week_start', 'lessons_completed', 'total_time_spent', 'average_score', 'active_days']
    list_filter = ['week_start', 'active_days']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']
    date_hierarchy = 'week_start'

@admin.register(MonthlyProgress)
class MonthlyProgressAdmin(admin.ModelAdmin):
    list_display = ['student', 'year', 'month', 'lessons_completed', 'total_time_spent', 'average_score', 'max_streak']
    list_filter = ['year', 'month', 'max_streak']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']

@admin.register(SubjectPerformance)
class SubjectPerformanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'lesson_type', 'completion_percentage', 'average_score', 'total_time_spent', 'last_updated']
    list_filter = ['lesson_type', 'last_updated']
    search_fields = ['student__username', 'student__first_name', 'student__last_name']
    readonly_fields = ['last_updated']

@admin.register(LearningActivity)
class LearningActivityAdmin(admin.ModelAdmin):
    list_display = ['student', 'activity_type', 'lesson', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['student__username', 'student__first_name', 'student__last_name', 'description']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']

# Teacher Communication Admin

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'years_experience', 'allow_parent_messages', 'response_time_hours']
    list_filter = ['allow_parent_messages', 'years_experience', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'specialization']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Teacher Information', {
            'fields': ('user', 'bio', 'specialization', 'years_experience')
        }),
        ('Communication Preferences', {
            'fields': ('allow_parent_messages', 'response_time_hours', 'preferred_contact_time')
        }),
        ('Contact Information', {
            'fields': ('office_location', 'office_hours')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'subject', 'class_name', 'is_class_teacher', 'is_active']
    list_filter = ['subject', 'is_class_teacher', 'is_active', 'created_at']
    search_fields = ['teacher__username', 'teacher__first_name', 'teacher__last_name', 'class_name']
    list_editable = ['is_active']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher')

@admin.register(TeacherMessage)
class TeacherMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'recipient', 'student', 'subject', 'message_type', 'priority', 'status', 'created_at']
    list_filter = ['message_type', 'priority', 'status', 'is_read', 'created_at']
    search_fields = ['sender__username', 'recipient__username', 'student__username', 'subject', 'content']
    readonly_fields = ['created_at', 'updated_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Message Details', {
            'fields': ('sender', 'recipient', 'student', 'subject', 'message_type', 'priority')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Status', {
            'fields': ('status', 'is_read', 'read_at')
        }),
        ('Threading', {
            'fields': ('parent_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'recipient', 'student')

@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = ['subject', 'student', 'participant_count', 'is_active', 'last_message_at', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_message_at']
    search_fields = ['subject', 'student__username', 'student__first_name', 'student__last_name']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at']
    
    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = 'Participants'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student').prefetch_related('participants')

@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available']
    search_fields = ['teacher__username', 'teacher__first_name', 'teacher__last_name']
    list_editable = ['is_available']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('teacher')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user__userprofile')


# Register Student model
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'email', 'course', 'created_at']
    list_filter = ['course', 'created_at']
    search_fields = ['name', 'email', 'course']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


# Register Parent model
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'relation', 'created_at']
    list_filter = ['relation', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


# Register Teacher model
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'email', 'experience', 'created_at']
    list_filter = ['subject', 'experience', 'created_at']
    search_fields = ['name', 'email', 'subject']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
