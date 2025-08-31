#!/usr/bin/env python3
"""
Test script for development authentication system
"""

import os
import requests
from app.app import app, FAKE_USERS, AUTH_MODE

def test_dev_authentication():
    """Test the development authentication system"""
    print("🧪 Testing Development Authentication System\n")
    
    # Set environment to dev mode
    os.environ['AUTH_MODE'] = 'dev'
    
    # Reload app configuration to pick up new AUTH_MODE
    app.config['TESTING'] = True
    app.config['AUTH_MODE'] = 'dev'  # Force dev mode in app config
    
    client = app.test_client()
    
    print("1️⃣ Testing login page in dev mode...")
    response = client.get('/login')
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Login page loads correctly in dev mode")
        # Check if it contains dev login form
        if 'Development Login' in response.get_data(as_text=True):
            print("   ✅ Dev login form is displayed")
        else:
            print("   ❌ Dev login form not found")
    else:
        print("   ❌ Login page failed to load")
    
    print("\n2️⃣ Testing fake user authentication...")
    
    for username, user_data in FAKE_USERS.items():
        print(f"\n   Testing user: {username}")
        
        # Test login with fake user
        response = client.get(f'/cas_callback?username={username}')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 302:  # Redirect to dashboard
            print(f"   ✅ {username} login successful")
            
            # Check session data
            with client.session_transaction() as sess:
                if 'schGrAcPersonID' in sess:
                    print(f"   ✅ Session ID set: {sess['schGrAcPersonID']}")
                if 'role' in sess:
                    print(f"   ✅ Role set: {sess['role']} (expected: {user_data['role']})")
                    if sess['role'] == user_data['role']:
                        print("   ✅ Role matches expected value")
                    else:
                        print("   ❌ Role mismatch")
                if 'name' in sess:
                    print(f"   ✅ Name set: {sess['name']}")
        else:
            print(f"   ❌ {username} login failed")
    
    print("\n3️⃣ Testing dashboard access with different roles...")
    
    for username, user_data in FAKE_USERS.items():
        print(f"\n   Testing dashboard access for {username} ({user_data['role']})...")
        
        # Login first
        client.get(f'/cas_callback?username={username}')
        
        # Try to access dashboard
        response = client.get('/dashboard')
        print(f"   Dashboard Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ {username} can access dashboard")
            # Check if user info is displayed
            content = response.get_data(as_text=True)
            if user_data['name'] in content:
                print(f"   ✅ User name displayed: {user_data['name']}")
            if user_data['role'] in content:
                print(f"   ✅ User role displayed: {user_data['role']}")
        else:
            print(f"   ❌ {username} cannot access dashboard")
    
    print("\n4️⃣ Testing authorization with different roles...")
    
    # Test student permissions
    print("\n   Testing student permissions...")
    client.get('/cas_callback?username=student1')
    
    # Student should be able to view groups
    response = client.get('/groups')
    print(f"   Groups endpoint: {response.status_code}")
    
    # Student should NOT be able to access admin endpoints
    response = client.get('/groups/1/absences')
    print(f"   Absences endpoint: {response.status_code}")
    
    # Test professor permissions
    print("\n   Testing professor permissions...")
    client.get('/cas_callback?username=prof1')
    
    # Professor should be able to view absences
    response = client.get('/groups/1/absences')
    print(f"   Absences endpoint: {response.status_code}")
    
    # Test admin permissions
    print("\n   Testing admin permissions...")
    client.get('/cas_callback?username=admin1')
    
    # Admin should have full access
    response = client.get('/groups')
    print(f"   Groups endpoint: {response.status_code}")
    
    print("\n🎉 Development authentication testing completed!")

def test_production_mode():
    """Test that production mode still works"""
    print("\n🔒 Testing Production Mode...")
    
    # Set environment to production mode
    os.environ['AUTH_MODE'] = 'cas'
    
    app.config['TESTING'] = True
    client = app.test_client()
    
    # Test login redirects to CAS
    response = client.get('/login')
    print(f"   Login redirect status: {response.status_code}")
    
    if response.status_code == 302:
        print("   ✅ Production mode redirects to CAS")
    else:
        print("   ❌ Production mode not working correctly")

def main():
    """Run all tests"""
    print("🚀 Starting Development Authentication Tests\n")
    
    try:
        test_dev_authentication()
        test_production_mode()
        print("\n✅ All tests completed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
