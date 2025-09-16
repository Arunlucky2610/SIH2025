#!/usr/bin/env python
"""
Simple script to create test users without MongoDB dependency
"""
import os
import sys
import django

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

from django.contrib.auth.models import User
from learning.models import UserProfile

def create_test_users():
    """Create test users for different roles"""
    
    # Test user data
    test_users = [
        {
            'username': 'teststudent',
            'email': 'student@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Student',
            'role': 'student',
            'extra_data': {'grade': '10'}
        },
        {
            'username': 'testparent',
            'email': 'parent@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Parent',
            'role': 'parent',
            'extra_data': {'child_name': 'Test Child'}
        },
        {
            'username': 'testteacher',
            'email': 'teacher@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Teacher',
            'role': 'teacher',
            'extra_data': {'subject': 'Mathematics'}
        }
    ]
    
    created_users = []
    
    for user_data in test_users:
        username = user_data['username']
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            print(f"User '{username}' already exists. Skipping...")
            continue
        
        # Create Django user
        user = User.objects.create_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name']
        )
        
        # Create UserProfile
        profile_data = {
            'user': user,
            'role': user_data['role'],
            'language_preference': 'en'
        }
        
        # Add role-specific data
        if user_data['role'] == 'student':
            profile_data['grade'] = user_data['extra_data']['grade']
        elif user_data['role'] == 'parent':
            profile_data['child_name'] = user_data['extra_data']['child_name']
        elif user_data['role'] == 'teacher':
            profile_data['subject'] = user_data['extra_data']['subject']
        
        UserProfile.objects.create(**profile_data)
        
        created_users.append(username)
        print(f"✅ Created {user_data['role']} user: {username}")
    
    if created_users:
        print(f"\n🎉 Successfully created {len(created_users)} test users!")
        print("\n📋 Test Login Credentials:")
        for user_data in test_users:
            if user_data['username'] in created_users:
                print(f"  {user_data['role'].title()}: {user_data['username']} / testpass123")
    else:
        print("ℹ️  All test users already exist.")
    
    print(f"\n🌐 You can now login at: http://127.0.0.1:8000/login/")

if __name__ == '__main__':
    create_test_users()