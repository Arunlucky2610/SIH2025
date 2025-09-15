"""
Teacher Communication Views
Views for handling communication between parents and teachers
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json

from .models import UserProfile, Lesson
from .teacher_communication_models import (
    TeacherMessage, TeacherAssignment, TeacherAvailability, 
    ConversationThread, TeacherProfile
)

@login_required
def teacher_communication_dashboard(request):
    """Main teacher communication dashboard for parents"""
    if request.user.userprofile.role != 'parent':
        messages.error(request, "Access denied. This section is for parents only.")
        return redirect('home')
    
    # Get parent's children
    children = request.user.userprofile.children.all()
    
    # Get recent conversations
    recent_conversations = ConversationThread.objects.filter(
        participants=request.user,
        is_active=True
    )[:5]
    
    # Get unread message count
    unread_count = TeacherMessage.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    context = {
        'children': children,
        'recent_conversations': recent_conversations,
        'unread_count': unread_count,
    }
    
    return render(request, 'learning/teacher_communication/dashboard.html', context)

@login_required
def select_teacher(request, child_id):
    """Select teacher to communicate with for a specific child"""
    if request.user.userprofile.role != 'parent':
        return redirect('home')
    
    # Verify child belongs to this parent
    try:
        child = User.objects.get(
            id=child_id,
            userprofile__parent=request.user.userprofile
        )
    except User.DoesNotExist:
        messages.error(request, "Child not found or access denied.")
        return redirect('teacher_communication_dashboard')
    
    # Get all teachers with their assignments
    teachers_data = []
    
    # Get class teachers (main teachers for the student)
    class_teachers = TeacherAssignment.objects.filter(
        is_class_teacher=True,
        is_active=True
    ).select_related('teacher', 'teacher__userprofile')
    
    # Get subject teachers
    subject_teachers = TeacherAssignment.objects.filter(
        is_active=True
    ).select_related('teacher', 'teacher__userprofile').exclude(
        teacher__in=[t.teacher for t in class_teachers]
    )
    
    # Organize teachers by type
    for assignment in class_teachers:
        try:
            teacher_profile = assignment.teacher.teacher_profile
        except:
            # Create teacher profile if it doesn't exist
            teacher_profile = TeacherProfile.objects.create(user=assignment.teacher)
        
        teachers_data.append({
            'teacher': assignment.teacher,
            'assignment': assignment,
            'profile': teacher_profile,
            'type': 'Class Teacher',
            'subjects': list(TeacherAssignment.objects.filter(
                teacher=assignment.teacher, 
                is_active=True
            ).values_list('subject', flat=True))
        })
    
    for assignment in subject_teachers:
        try:
            teacher_profile = assignment.teacher.teacher_profile
        except:
            teacher_profile = TeacherProfile.objects.create(user=assignment.teacher)
        
        teachers_data.append({
            'teacher': assignment.teacher,
            'assignment': assignment,
            'profile': teacher_profile,
            'type': 'Subject Teacher',
            'subjects': [assignment.subject]
        })
    
    context = {
        'child': child,
        'teachers_data': teachers_data,
    }
    
    return render(request, 'learning/teacher_communication/select_teacher.html', context)

@login_required
def compose_message(request, child_id, teacher_id):
    """Compose a new message to a teacher"""
    if request.user.userprofile.role != 'parent':
        return redirect('home')
    
    # Verify child belongs to this parent
    try:
        child = User.objects.get(
            id=child_id,
            userprofile__parent=request.user.userprofile
        )
    except User.DoesNotExist:
        messages.error(request, "Child not found or access denied.")
        return redirect('teacher_communication_dashboard')
    
    # Verify teacher exists and is a teacher
    try:
        teacher = User.objects.get(
            id=teacher_id,
            userprofile__role='teacher'
        )
    except User.DoesNotExist:
        messages.error(request, "Teacher not found.")
        return redirect('select_teacher', child_id=child_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        content = request.POST.get('content', '').strip()
        message_type = request.POST.get('message_type', 'inquiry')
        priority = request.POST.get('priority', 'normal')
        
        if not subject or not content:
            messages.error(request, "Subject and message content are required.")
        else:
            # Create the message
            message = TeacherMessage.objects.create(
                sender=request.user,
                recipient=teacher,
                student=child,
                subject=subject,
                content=content,
                message_type=message_type,
                priority=priority
            )
            
            # Create or update conversation thread
            thread, created = ConversationThread.objects.get_or_create(
                student=child,
                subject=subject,
                defaults={'last_message_at': timezone.now()}
            )
            thread.participants.add(request.user, teacher)
            if not created:
                thread.last_message_at = timezone.now()
                thread.save()
            
            messages.success(request, f"Message sent to {teacher.get_full_name() or teacher.username} successfully!")
            return redirect('conversation_detail', thread_id=thread.id)
    
    # Get teacher's profile and assignments
    try:
        teacher_profile = teacher.teacher_profile
    except:
        teacher_profile = TeacherProfile.objects.create(user=teacher)
    
    teacher_assignments = TeacherAssignment.objects.filter(
        teacher=teacher,
        is_active=True
    )
    
    context = {
        'child': child,
        'teacher': teacher,
        'teacher_profile': teacher_profile,
        'teacher_assignments': teacher_assignments,
        'message_types': TeacherMessage.MESSAGE_TYPES,
        'priority_choices': TeacherMessage.PRIORITY_CHOICES,
    }
    
    return render(request, 'learning/teacher_communication/compose_message.html', context)

@login_required
def conversation_list(request):
    """List all conversations for the current user"""
    conversations = ConversationThread.objects.filter(
        participants=request.user,
        is_active=True
    ).annotate(
        message_count=Count('participants__sent_teacher_messages'),
        last_message_time=Max('participants__sent_teacher_messages__created_at')
    )
    
    # Add unread count for each conversation
    for conversation in conversations:
        conversation.unread_count = TeacherMessage.objects.filter(
            student=conversation.student,
            recipient=request.user,
            is_read=False
        ).count()
    
    context = {
        'conversations': conversations,
    }
    
    return render(request, 'learning/teacher_communication/conversation_list.html', context)

@login_required
def conversation_detail(request, thread_id):
    """View detailed conversation thread"""
    thread = get_object_or_404(ConversationThread, id=thread_id)
    
    # Check if user is participant
    if not thread.participants.filter(id=request.user.id).exists():
        messages.error(request, "Access denied to this conversation.")
        return redirect('conversation_list')
    
    # Get all messages in this thread
    messages_in_thread = TeacherMessage.objects.filter(
        Q(student=thread.student) &
        Q(
            Q(sender__in=thread.participants.all()) |
            Q(recipient__in=thread.participants.all())
        )
    ).order_by('created_at')
    
    # Mark messages as read
    TeacherMessage.objects.filter(
        student=thread.student,
        recipient=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now(), status='read')
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            # Find the other participant (teacher or parent)
            other_participants = thread.participants.exclude(id=request.user.id)
            if other_participants.exists():
                recipient = other_participants.first()
                
                # Create reply message
                TeacherMessage.objects.create(
                    sender=request.user,
                    recipient=recipient,
                    student=thread.student,
                    subject=f"Re: {thread.subject}",
                    content=content,
                    message_type='inquiry'  # Default for replies
                )
                
                # Update thread timestamp
                thread.last_message_at = timezone.now()
                thread.save()
                
                messages.success(request, "Reply sent successfully!")
                return redirect('conversation_detail', thread_id=thread.id)
    
    context = {
        'thread': thread,
        'messages': messages_in_thread,
    }
    
    return render(request, 'learning/teacher_communication/conversation_detail.html', context)

@login_required
@csrf_exempt
def mark_message_read(request):
    """AJAX endpoint to mark message as read"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')
            
            message = TeacherMessage.objects.get(
                id=message_id,
                recipient=request.user
            )
            message.mark_as_read()
            
            return JsonResponse({'status': 'success'})
        except TeacherMessage.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Message not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def get_child_teachers(request, child_id):
    """AJAX endpoint to get teachers for a specific child"""
    if request.user.userprofile.role != 'parent':
        return JsonResponse({'error': 'Access denied'})
    
    try:
        child = User.objects.get(
            id=child_id,
            userprofile__parent=request.user.userprofile
        )
    except User.DoesNotExist:
        return JsonResponse({'error': 'Child not found'})
    
    # Get child's current lessons/subjects
    child_subjects = set()
    if hasattr(child, 'progress'):
        child_subjects = set(
            child.progress.values_list('lesson__lesson_type', flat=True).distinct()
        )
    
    # Get teachers for these subjects
    teachers = []
    teacher_assignments = TeacherAssignment.objects.filter(
        subject__in=child_subjects,
        is_active=True
    ).select_related('teacher', 'teacher__userprofile')
    
    for assignment in teacher_assignments:
        teacher_data = {
            'id': assignment.teacher.id,
            'name': assignment.teacher.get_full_name() or assignment.teacher.username,
            'subject': assignment.get_subject_display(),
            'is_class_teacher': assignment.is_class_teacher,
        }
        
        # Get teacher profile if exists
        try:
            profile = assignment.teacher.teacher_profile
            teacher_data.update({
                'bio': profile.bio,
                'specialization': profile.specialization,
                'years_experience': profile.years_experience,
            })
        except:
            pass
        
        teachers.append(teacher_data)
    
    return JsonResponse({'teachers': teachers})

# Additional utility views for teacher communication

@login_required
def teacher_availability(request, teacher_id):
    """Get teacher availability information"""
    try:
        teacher = User.objects.get(id=teacher_id, userprofile__role='teacher')
        availability = TeacherAvailability.objects.filter(
            teacher=teacher,
            is_available=True
        ).order_by('day_of_week', 'start_time')
        
        availability_data = []
        for slot in availability:
            availability_data.append({
                'day': slot.get_day_of_week_display(),
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'notes': slot.notes,
            })
        
        return JsonResponse({'availability': availability_data})
    except User.DoesNotExist:
        return JsonResponse({'error': 'Teacher not found'})

@login_required
def search_teachers(request):
    """Search teachers by name or subject"""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'teachers': []})
    
    # Search teachers by name or subject
    teachers = User.objects.filter(
        Q(userprofile__role='teacher') &
        (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(teacher_assignments__subject__icontains=query)
        )
    ).distinct()
    
    teacher_data = []
    for teacher in teachers:
        assignments = TeacherAssignment.objects.filter(teacher=teacher, is_active=True)
        subjects = [a.get_subject_display() for a in assignments]
        
        teacher_data.append({
            'id': teacher.id,
            'name': teacher.get_full_name() or teacher.username,
            'username': teacher.username,
            'subjects': subjects,
            'is_class_teacher': assignments.filter(is_class_teacher=True).exists(),
        })
    
    return JsonResponse({'teachers': teacher_data})