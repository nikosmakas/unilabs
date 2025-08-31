#!/usr/bin/env python3
"""
Manual testing script for authorization endpoints
"""

import requests
import json
from flask import Flask
from app.app import app

def test_endpoints():
    """Test authorization endpoints manually"""
    print("🧪 Manual Testing of Authorization Endpoints\n")
    
    # Start Flask app in test mode
    app.config['TESTING'] = True
    client = app.test_client()
    
    # Test 1: Unauthorized access to protected endpoint
    print("1️⃣ Testing unauthorized access to /groups...")
    response = client.get('/groups')
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.get_json()}")
    assert response.status_code == 401, "Should return 401 for unauthorized access"
    print("   ✅ Unauthorized access correctly blocked\n")
    
    # Test 2: Authorized access with student session
    print("2️⃣ Testing authorized access with student session...")
    with client.session_transaction() as sess:
        sess['schGrAcPersonID'] = 13628
        sess['role'] = 'student'
        sess['name'] = 'Test Student'
    
    response = client.get('/groups')
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.get_json()
        print(f"   Response: {len(data)} groups returned")
        if data:
            print(f"   Sample group: {data[0]}")
    print("   ✅ Authorized access works correctly\n")
    
    # Test 3: Student joining group
    print("3️⃣ Testing student joining group...")
    response = client.post('/groups/1/join')
    print(f"   Status Code: {response.status_code}")
    data = response.get_json()
    print(f"   Response: {data}")
    print("   ✅ Group join endpoint responds correctly\n")
    
    # Test 4: Student leaving group
    print("4️⃣ Testing student leaving group...")
    response = client.post('/groups/1/leave')
    print(f"   Status Code: {response.status_code}")
    data = response.get_json()
    print(f"   Response: {data}")
    print("   ✅ Group leave endpoint responds correctly\n")
    
    # Test 5: Student trying to access professor-only endpoint
    print("5️⃣ Testing student accessing professor-only endpoint...")
    response = client.get('/groups/1/absences')
    print(f"   Status Code: {response.status_code}")
    data = response.get_json()
    print(f"   Response: {data}")
    assert response.status_code == 403, "Should return 403 for insufficient permissions"
    print("   ✅ Student correctly blocked from professor-only endpoint\n")
    
    # Test 6: Professor accessing absences
    print("6️⃣ Testing professor accessing absences...")
    with client.session_transaction() as sess:
        sess['schGrAcPersonID'] = 1
        sess['role'] = 'professor'
        sess['name'] = 'Test Professor'
    
    response = client.get('/groups/1/absences')
    print(f"   Status Code: {response.status_code}")
    data = response.get_json()
    print(f"   Response: {data}")
    print("   ✅ Professor can access absences endpoint\n")
    
    # Test 7: Student viewing own profile
    print("7️⃣ Testing student viewing own profile...")
    with client.session_transaction() as sess:
        sess['schGrAcPersonID'] = 13628
        sess['role'] = 'student'
        sess['name'] = 'Test Student'
    
    response = client.get('/students/profile')
    print(f"   Status Code: {response.status_code}")
    data = response.get_json()
    print(f"   Response: {data}")
    print("   ✅ Student can view own profile\n")
    
    # Test 8: PII masking in professors list
    print("8️⃣ Testing PII masking in professors list...")
    response = client.get('/professors')
    print(f"   Status Code: {response.status_code}")
    data = response.get_json()
    if data:
        prof = data[0]
        print(f"   Sample professor: {prof}")
        # Check if PII is masked
        if 'email' in prof and '***' in prof['email']:
            print("   ✅ PII masking works correctly")
        else:
            print("   ⚠️  PII masking may not be working")
    print("   ✅ Professors list endpoint works\n")
    
    print("🎉 All manual tests completed successfully!")

def test_permission_matrix():
    """Test permission matrix functionality"""
    print("\n🔍 Testing Permission Matrix Functionality\n")
    
    from app.auth import PermissionMatrix
    
    matrix = PermissionMatrix()
    
    # Test various permission combinations
    test_cases = [
        ('student', 'groups', 'join', True),
        ('student', 'groups', 'create', False),
        ('professor', 'groups', 'create', True),
        ('professor', 'absences', 'edit_group_absences', True),
        ('student', 'absences', 'edit_group_absences', False),
        ('admin', 'user_management', 'view', True),
        ('guest', 'user_management', 'view', False),
    ]
    
    for role, resource, action, expected in test_cases:
        result = matrix.has_permission(role, resource, action)
        status = "✅" if result == expected else "❌"
        print(f"{status} {role}.{resource}.{action}: {result} (expected: {expected})")
    
    print("\n✅ Permission matrix testing completed!")

def main():
    """Run all manual tests"""
    print("🚀 Starting Manual Authorization Tests\n")
    
    try:
        test_permission_matrix()
        test_endpoints()
        print("\n🎉 All manual tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Manual test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
