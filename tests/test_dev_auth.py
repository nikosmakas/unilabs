#!/usr/bin/env python3
"""
Test script for development authentication system
Run from project root: python -m pytest tests/test_dev_auth.py
Or: cd thesis/unilabs && python tests/test_dev_auth.py
"""

import os
import sys

# Add app directory to path for imports
APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app')
sys.path.insert(0, APP_DIR)

from app import app, FAKE_USERS

def test_dev_authentication():
    """Test the development authentication system"""
    print("🧪 Testing Development Authentication System\n")
    
    os.environ['AUTH_MODE'] = 'dev'
    
    app.config['TESTING'] = True
    app.config['AUTH_MODE'] = 'dev'
    
    client = app.test_client()
    
    print("1️⃣ Testing login page in dev mode...")
    response = client.get('/login')
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Login page loads correctly in dev mode")
        if 'Development Login' in response.get_data(as_text=True):
            print("   ✅ Dev login form is displayed")
        else:
            print("   ❌ Dev login form not found")
    else:
        print("   ❌ Login page failed to load")
    
    print("\n2️⃣ Testing fake user authentication...")
    
    for username, user_data in FAKE_USERS.items():
        print(f"\n   Testing user: {username}")
        
        response = client.get(f'/cas_callback?username={username}')
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 302:
            print(f"   ✅ {username} login successful")
            
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
        
        client.get(f'/cas_callback?username={username}')
        
        response = client.get('/dashboard')
        print(f"   Dashboard Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ {username} can access dashboard")
            content = response.get_data(as_text=True)
            if user_data['name'] in content:
                print(f"   ✅ User name displayed: {user_data['name']}")
        else:
            print(f"   ❌ {username} cannot access dashboard")
    
    print("\n4️⃣ Testing authorization with different roles...")
    
    print("\n   Testing student permissions...")
    client.get('/cas_callback?username=student1')
    
    response = client.get('/groups')
    print(f"   Groups endpoint: {response.status_code} (expected: 200)")
    
    response = client.get('/groups/1/absences')
    print(f"   Absences endpoint: {response.status_code} (expected: 403 for student)")
    
    print("\n   Testing professor permissions...")
    client.get('/cas_callback?username=prof1')
    
    response = client.get('/groups/1/absences')
    print(f"   Absences endpoint: {response.status_code} (expected: 200 for professor)")
    
    print("\n🎉 Development authentication testing completed!")

def test_production_mode():
    """Test that production mode still works"""
    print("\n🔒 Testing Production Mode...")
    
    os.environ['AUTH_MODE'] = 'cas'
    app.config['AUTH_MODE'] = 'cas'
    client = app.test_client()
    
    response = client.get('/login', follow_redirects=False)
    print(f"   Login redirect status: {response.status_code}")
    
    if response.status_code == 302:
        location = response.headers.get('Location', '')
        if 'sso.uoi.gr' in location:
            print("   ✅ Production mode redirects to CAS")
        else:
            print(f"   ⚠️ Redirects to: {location}")
    else:
        print("   ❌ Production mode not working correctly")

def main():
    """Run all tests"""
    print("🚀 Starting Development Authentication Tests\n")
    
    try:
        test_dev_authentication()
        test_production_mode()
        print("\n✅ All tests completed!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
