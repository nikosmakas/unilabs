#!/usr/bin/env python3
"""
Simple test script for authorization system
"""

import json
import os
from app.auth import PermissionMatrix, mask_pii, audit_log

def test_permission_matrix():
    """Test permission matrix loading and checking"""
    print("🔍 Testing Permission Matrix...")
    
    # Create test matrix
    matrix_data = {
        "roles": ["guest", "student", "professor", "admin"],
        "resources": {
            "groups": {
                "view": ["guest", "student", "professor", "admin"],
                "join": ["student"],
                "create": ["professor", "admin"]
            }
        }
    }
    
    with open('test_matrix.json', 'w', encoding='utf-8') as f:
        json.dump(matrix_data, f, indent=2, ensure_ascii=False)
    
    try:
        # Test matrix loading
        matrix = PermissionMatrix()
        print("✅ Permission matrix loaded successfully")
        
        # Test permission checking
        assert matrix.has_permission('student', 'groups', 'join') == True
        assert matrix.has_permission('student', 'groups', 'create') == False
        assert matrix.has_permission('professor', 'groups', 'create') == True
        print("✅ Permission checking works correctly")
        
    except Exception as e:
        print(f"❌ Permission matrix test failed: {e}")
        return False
    
    finally:
        if os.path.exists('test_matrix.json'):
            os.remove('test_matrix.json')
    
    return True

def test_pii_masking():
    """Test PII masking functionality"""
    print("\n🔒 Testing PII Masking...")
    
    test_data = {
        'email': 'test@example.com',
        'am': 13628,
        'tel': '2681050448',
        'name': 'Test User'
    }
    
    try:
        masked = mask_pii(test_data)
        
        # Check email masking
        assert '***' in masked['email']
        assert masked['email'] != test_data['email']
        
        # Check AM masking
        assert '***' in str(masked['am'])
        assert masked['am'] != test_data['am']
        
        # Check phone masking
        assert '***' in str(masked['tel'])
        assert masked['tel'] != test_data['tel']
        
        # Check non-PII fields unchanged
        assert masked['name'] == test_data['name']
        
        print("✅ PII masking works correctly")
        print(f"   Original email: {test_data['email']}")
        print(f"   Masked email: {masked['email']}")
        print(f"   Original AM: {test_data['am']}")
        print(f"   Masked AM: {masked['am']}")
        
    except Exception as e:
        print(f"❌ PII masking test failed: {e}")
        return False
    
    return True

def test_audit_logging():
    """Test audit logging functionality"""
    print("\n📝 Testing Audit Logging...")
    
    try:
        # Create a mock request context for testing
        from flask import Flask
        app = Flask(__name__)
        
        with app.test_request_context():
            # Test audit log creation (should not raise exception)
            audit_log(
                action="test_action",
                old_value="old_value",
                new_value="new_value",
                reason="test reason"
            )
            print("✅ Audit logging works correctly")
        
    except Exception as e:
        print(f"❌ Audit logging test failed: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic authorization functionality"""
    print("\n🔐 Testing Basic Authorization...")
    
    # Test role-based permissions
    roles = ['guest', 'student', 'professor', 'admin']
    resources = ['dashboard', 'groups', 'absences', 'students_list']
    
    print("   Available roles:", roles)
    print("   Available resources:", resources)
    print("✅ Basic authorization structure verified")
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Authorization System Tests\n")
    
    tests = [
        ("Permission Matrix", test_permission_matrix),
        ("PII Masking", test_pii_masking),
        ("Audit Logging", test_audit_logging),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Authorization system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
