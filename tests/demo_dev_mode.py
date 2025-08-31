#!/usr/bin/env python3
"""
Demo script for development authentication mode
"""

import os
from app.app import app, FAKE_USERS

def demo_dev_mode():
    """Demonstrate the development authentication mode"""
    print("🔧 Development Authentication Mode Demo\n")
    
    # Set dev mode
    os.environ['AUTH_MODE'] = 'dev'
    app.config['AUTH_MODE'] = 'dev'
    
    print("✅ Development mode enabled")
    print(f"📋 Available test users: {len(FAKE_USERS)}")
    
    for username, user_data in FAKE_USERS.items():
        print(f"\n👤 {username}:")
        print(f"   Name: {user_data['name']}")
        print(f"   Role: {user_data['role']}")
        print(f"   ID: {user_data.get('am', user_data.get('prof_id', user_data.get('admin_id')))}")
        print(f"   Email: {user_data['email']}")
    
    print("\n🚀 To test the dev mode:")
    print("1. Set environment variable: export AUTH_MODE=dev")
    print("2. Start the application: python app.py")
    print("3. Navigate to: http://localhost:5000/login")
    print("4. Select any test user to login")
    print("5. Test different authorization levels")
    
    print("\n🔐 Authorization Testing:")
    print("- Login as student1: Can view groups, join/leave groups")
    print("- Login as prof1: Can manage groups, view/edit absences")
    print("- Login as admin1: Full access to all features")
    
    print("\n⚠️  REMEMBER: This is for development/testing only!")
    print("   NEVER enable in production!")

if __name__ == "__main__":
    demo_dev_mode()
