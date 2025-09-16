#!/usr/bin/env python
"""
Simple account creation script - No MongoDB required
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

from django.contrib.auth.models import User
from learning.models import UserProfile

def create_account():
    """Interactive account creation"""
    
    print("=== CREATE NEW ACCOUNT ===")
    print("Available roles: student, teacher, parent")
    
    # Get input
    role = input("Enter role (student/teacher/parent): ").strip().lower()
    if role not in ['student', 'teacher', 'parent']:
        print("❌ Invalid role! Please use: student, teacher, or parent")
        return
    
    username = input("Enter username (3+ characters): ").strip()
    if len(username) < 3:
        print("❌ Username must be at least 3 characters!")
        return
    
    if User.objects.filter(username=username).exists():
        print(f"❌ Username '{username}' already exists!")
        return
    
    email = input("Enter email: ").strip()
    if '@' not in email:
        print("❌ Please enter a valid email!")
        return
    
    if User.objects.filter(email=email).exists():
        print(f"❌ Email '{email}' already exists!")
        return
    
    password = input("Enter password (6+ characters): ").strip()
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return
    
    # Additional info
    first_name = input("Enter first name: ").strip()
    last_name = input("Enter last name: ").strip()
    
    try:
        # Create Django user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create UserProfile
        profile_data = {
            'user': user,
            'role': role,
            'language_preference': 'en'
        }
        
        if role == 'student':
            grade = input("Enter grade/class: ").strip()
            profile_data['grade'] = grade
        elif role == 'teacher':
            subject = input("Enter subject: ").strip()
            profile_data['subject'] = subject
        elif role == 'parent':
            child_name = input("Enter child's name: ").strip()
            profile_data['child_name'] = child_name
        
        UserProfile.objects.create(**profile_data)
        
        print(f"\n✅ SUCCESS! Account created for {role}: {username}")
        print(f"\n📋 Login Credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  Role: {role.title()}")
        print(f"\n🌐 Login at: http://127.0.0.1:8000/login/")
        
    except Exception as e:
        print(f"❌ Error creating account: {e}")

if __name__ == '__main__':
    create_account()