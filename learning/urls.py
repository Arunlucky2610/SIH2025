from django.urls import path
from . import views

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
]