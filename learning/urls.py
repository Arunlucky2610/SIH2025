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
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),
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
    path('lesson/<int:lesson_id>/complete/', views.mark_lesson_complete, name='mark_lesson_complete'),
    
    # Quiz
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    
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
    
    # Student, Parent, Teacher CRUD
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('parents/', views.parent_list, name='parent_list'),
    path('parents/create/', views.parent_create, name='parent_create'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/create/', views.teacher_create, name='teacher_create'),
]