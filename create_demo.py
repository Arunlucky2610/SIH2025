#!/usr/bin/env python
"""
Quick test to create a user account manually
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

def create_demo_account():
    """Create a demo parent account"""
    
    username = "demo_parent"
    email = "demo@parent.com"
    password = "demo123"
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"Demo user '{username}' already exists!")
        user = User.objects.get(username=username)
    else:
        # Create Django user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name='Demo',
            last_name='Parent'
        )
        
        # Create UserProfile
        UserProfile.objects.create(
            user=user,
            role='parent',
            language_preference='en',
            child_name='Demo Child'
        )
        
        print(f"✅ Created demo parent account!")
    
    print(f"\n📋 Demo Login Credentials:")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Role: Parent")
    print(f"\n🌐 Login at: http://127.0.0.1:8000/login/")

if __name__ == '__main__':
    create_demo_account()