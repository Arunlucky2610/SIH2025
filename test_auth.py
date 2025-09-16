#!/usr/bin/env python
"""
Test user authentication and passwords
"""
import os
import sys
import django

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rural_edu.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from learning.models import UserProfile

def test_user_login():
    """Test login for all users"""
    
    print("=== TESTING USER AUTHENTICATION ===\n")
    
    # Test users with their passwords
    test_credentials = [
        ('teststudent', 'testpass123'),
        ('testparent', 'testpass123'),
        ('testteacher', 'testpass123'),
        ('arun', 'arun2005'),  # New user created via signup
    ]
    
    for username, password in test_credentials:
        print(f"Testing user: {username}")
        
        # Check if user exists
        try:
            user = User.objects.get(username=username)
            print(f"  ✅ User exists: {user.username} ({user.email})")
            print(f"  ✅ Active: {user.is_active}")
            
            # Test authentication
            auth_user = authenticate(username=username, password=password)
            if auth_user:
                print(f"  ✅ Authentication SUCCESS for {username}")
                
                # Check profile
                try:
                    profile = user.userprofile
                    print(f"  ✅ Profile exists: Role = {profile.role}")
                except UserProfile.DoesNotExist:
                    print(f"  ❌ No UserProfile found for {username}")
                    
            else:
                print(f"  ❌ Authentication FAILED for {username}")
                
                # Try to check if password is set correctly
                if user.check_password(password):
                    print(f"    🔍 Password check passed - auth might have other issues")
                else:
                    print(f"    🔍 Password check failed - password is incorrect")
                    
        except User.DoesNotExist:
            print(f"  ❌ User {username} does not exist")
            
        print()
    
    print("=== USER SUMMARY ===")
    all_users = User.objects.all()
    for user in all_users:
        try:
            profile = user.userprofile
            role = profile.role
        except:
            role = "No Profile"
        print(f"  {user.username} | {user.email} | {role} | Active: {user.is_active}")

if __name__ == '__main__':
    test_user_login()