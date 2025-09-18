from django.urls import path
from . import views
from . import teacher_communication_views

urlpatterns = [
    # Authentication
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    
    # Dashboards
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('teacher/', views.teacher_home, name='teacher_home'),
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/reports/', views.teacher_reports, name='teacher_reports'),
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('parents/parent-dashboard-test/', views.parent_dashboard, name='parent_dashboard_test'),
    path('parents/ultra-dashboard/', views.parent_dashboard, name='parent_dashboard_ultra'),
    path('parents/analytics/', views.parent_analytics, name='parent_analytics'),
    
    # Notifications (for parents)
    path('notifications/', views.notifications_view, name='notifications'),
    path('notification-settings/', views.notification_settings, name='notification_settings'),
    
    # Teacher Communication
    path('teacher-communication/', teacher_communication_views.teacher_communication_dashboard, name='teacher_communication_dashboard'),
    path('teacher-communication/child/<int:child_id>/select-teacher/', teacher_communication_views.select_teacher, name='select_teacher'),
    path('teacher-communication/child/<int:child_id>/teacher/<int:teacher_id>/compose/', teacher_communication_views.compose_message, name='compose_message'),
    path('teacher-communication/conversations/', teacher_communication_views.conversation_list, name='conversation_list'),
    path('teacher-communication/conversation/<int:thread_id>/', teacher_communication_views.conversation_detail, name='conversation_detail'),
    path('teacher-communication/mark-message-read/', teacher_communication_views.mark_message_read, name='mark_message_read'),
    path('teacher-communication/child/<int:child_id>/teachers/', teacher_communication_views.get_child_teachers, name='get_child_teachers'),
    path('teacher-communication/teacher/<int:teacher_id>/availability/', teacher_communication_views.teacher_availability, name='teacher_availability'),
    path('teacher-communication/search-teachers/', teacher_communication_views.search_teachers, name='search_teachers'),
    
    # Lessons
    path('lesson/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('lesson/<int:lesson_id>/download/', views.download_lesson, name='download_lesson'),
    path('lesson/<int:lesson_id>/view/', views.view_lesson_file, name='view_lesson_file'),
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    
    # Quiz
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('quiz-result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    
    # PWA
    path('manifest.json', views.manifest, name='manifest'),
    path('offline/', views.offline, name='offline'),
    
    # Admin
    path('admin/stats/', views.admin_stats, name='admin_stats'),
    
    # Custom Admin for Parents and Teachers
    path('panel/', views.custom_admin_login, name='custom_admin_login'),
    path('panel/dashboard/', views.custom_admin_dashboard, name='custom_admin_dashboard'),
    path('panel/lessons/', views.custom_admin_lessons, name='custom_admin_lessons'),
    path('panel/lessons/add/', views.custom_admin_add_lesson, name='custom_admin_add_lesson'),
    path('panel/students/', views.custom_admin_students, name='custom_admin_students'),
    path('panel/student/<int:student_id>/', views.student_detail_view, name='student_detail_view'),
    path('send-message/', views.send_message, name='send_message'),
    
    # Quiz Management
    path('create-quiz/', views.create_quiz, name='create_quiz'),
    path('create-quick-quiz/', views.create_quick_quiz, name='create_quick_quiz'),
    path('schedule-quiz/', views.schedule_quiz, name='schedule_quiz'),
    path('publish-quiz/<int:quiz_id>/', views.publish_quiz, name='publish_quiz'),
    path('delete-quiz/<int:quiz_id>/', views.delete_quiz, name='delete_quiz'),
    path('delete-lesson/<int:lesson_id>/', views.delete_lesson, name='delete_lesson'),
    path('edit-quiz/<int:quiz_id>/', views.edit_quiz, name='edit_quiz'),
    
    # Student, Parent, Teacher CRUD
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('parents/', views.parent_list, name='parent_list'),
    path('parents/create/', views.parent_create, name='parent_create'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/create/', views.teacher_create, name='teacher_create'),
]