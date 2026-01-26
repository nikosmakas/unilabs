"""
Test script για τα APIs του UniLabs
Εκτέλεση: python test_apis.py
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

# Session για να διατηρούμε τα cookies
session = requests.Session()

def print_result(test_name, success, response=None, expected=None):
    """Εκτύπωση αποτελέσματος test"""
    status = '✅ PASS' if success else '❌ FAIL'
    print(f"{status} - {test_name}")
    if not success and response:
        print(f"   Response: {response}")
        if expected:
            print(f"   Expected: {expected}")

def test_login_dev():
    """Test: Development login"""
    print("\n" + "="*60)
    print("TEST: Development Login")
    print("="*60)
    
    # Login as student1
    response = session.get(f"{BASE_URL}/cas_callback?username=student1", allow_redirects=False)
    
    # Πρέπει να κάνει redirect στο dashboard
    success = response.status_code == 302 and '/dashboard' in response.headers.get('Location', '')
    print_result("Login redirect to dashboard", success, response.status_code)
    
    # Follow redirect
    response = session.get(f"{BASE_URL}/dashboard")
    success = response.status_code == 200 and 'Dashboard' in response.text
    print_result("Dashboard loads successfully", success)
    
    return success

def test_api_semesters():
    """Test: GET /api/semesters"""
    print("\n" + "="*60)
    print("TEST: API Semesters")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/semesters")
    data = response.json()
    
    success = data.get('success') == True and len(data.get('data', [])) > 0
    print_result("Get semesters", success, data)
    
    if success:
        print(f"   Found {len(data['data'])} semesters: {[s['name'] for s in data['data']]}")
    
    return success, data

def test_api_courses(semester):
    """Test: GET /api/courses/<semester>"""
    print("\n" + "="*60)
    print(f"TEST: API Courses for semester '{semester}'")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/courses/{semester}")
    data = response.json()
    
    success = data.get('success') == True
    print_result(f"Get courses for {semester}", success, data)
    
    if success and data.get('data'):
        print(f"   Found {len(data['data'])} courses: {[c['name'] for c in data['data']]}")
    
    return success, data

def test_api_labs(course_id):
    """Test: GET /api/labs/<course_id>"""
    print("\n" + "="*60)
    print(f"TEST: API Labs for course {course_id}")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/labs/{course_id}")
    data = response.json()
    
    success = data.get('success') == True
    print_result(f"Get labs for course {course_id}", success, data)
    
    if success and data.get('data'):
        print(f"   Found {len(data['data'])} labs: {[l['name'] for l in data['data']]}")
    
    return success, data

def test_api_groups(lab_id):
    """Test: GET /api/groups/<lab_id>"""
    print("\n" + "="*60)
    print(f"TEST: API Groups for lab {lab_id}")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/groups/{lab_id}")
    data = response.json()
    
    success = data.get('success') == True
    print_result(f"Get groups for lab {lab_id}", success, data)
    
    if success:
        print(f"   Lab: {data.get('lab_name')}")
        print(f"   Registration open: {data.get('registration_open')}")
        print(f"   Reg limit: {data.get('reg_limit')}")
        if data.get('data'):
            for g in data['data']:
                occ = g.get('occupancy', {})
                print(f"   - Group {g['group_id']}: {g['daytime']} ({occ.get('current', 0)}/{occ.get('max', 0)})")
    
    return success, data

def test_api_enrollment_status(lab_id):
    """Test: GET /api/student/enrollment-status/<lab_id>"""
    print("\n" + "="*60)
    print(f"TEST: API Enrollment Status for lab {lab_id}")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/student/enrollment-status/{lab_id}")
    data = response.json()
    
    success = data.get('success') == True
    print_result(f"Get enrollment status for lab {lab_id}", success, data)
    
    if success:
        print(f"   Is enrolled: {data.get('is_enrolled')}")
        print(f"   Can register: {data.get('can_register')}")
        print(f"   Can change group: {data.get('can_change_group')}")
        if data.get('current_group'):
            print(f"   Current group: {data['current_group']}")
    
    return success, data

def test_api_register_lab(lab_id, group_id):
    """Test: POST /api/register-lab"""
    print("\n" + "="*60)
    print(f"TEST: API Register to lab {lab_id}, group {group_id}")
    print("="*60)
    
    response = session.post(
        f"{BASE_URL}/api/register-lab",
        json={'lab_id': lab_id, 'group_id': group_id},
        headers={'Content-Type': 'application/json'}
    )
    data = response.json()
    
    print_result(f"Register to lab {lab_id}, group {group_id}", data.get('success'), data)
    print(f"   Message: {data.get('message')}")
    
    return data.get('success'), data

def test_api_student_enrollments():
    """Test: GET /api/student/enrollments"""
    print("\n" + "="*60)
    print("TEST: API Student Enrollments")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/student/enrollments")
    data = response.json()
    
    success = data.get('success') == True
    print_result("Get student enrollments", success, data)
    
    if success and data.get('data'):
        print(f"   Found {len(data['data'])} enrollments:")
        for e in data['data']:
            print(f"   - {e['lab_name']}: {e['group_daytime']} ({e['status']})")
    
    return success, data

def test_api_change_group(lab_id, old_group_id, new_group_id):
    """Test: PUT /api/change-group"""
    print("\n" + "="*60)
    print(f"TEST: API Change group from {old_group_id} to {new_group_id}")
    print("="*60)
    
    response = session.put(
        f"{BASE_URL}/api/change-group",
        json={
            'lab_id': lab_id,
            'old_group_id': old_group_id,
            'new_group_id': new_group_id
        },
        headers={'Content-Type': 'application/json'}
    )
    data = response.json()
    
    print_result(f"Change group from {old_group_id} to {new_group_id}", data.get('success'), data)
    print(f"   Message: {data.get('message')}")
    
    return data.get('success'), data

def test_api_group_professor(group_id):
    """Test: GET /api/groups/<group_id>/professor"""
    print("\n" + "="*60)
    print(f"TEST: API Group Professor for group {group_id}")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/groups/{group_id}/professor")
    data = response.json()
    
    success = data.get('success') == True
    print_result(f"Get professor for group {group_id}", success, data)
    
    if success and data.get('data'):
        for p in data['data']:
            print(f"   - {p['name']} ({p['status']}): {p['email']}")
    
    return success, data

def test_api_academic_year():
    """Test: GET /api/academic-year"""
    print("\n" + "="*60)
    print("TEST: API Academic Year")
    print("="*60)
    
    response = session.get(f"{BASE_URL}/api/academic-year")
    data = response.json()
    
    success = data.get('success') == True and data.get('academic_year') == 2025
    print_result("Get academic year", success, data)
    print(f"   Academic year: {data.get('academic_year')}")
    
    return success, data

def run_all_tests():
    """Εκτέλεση όλων των tests"""
    print("\n" + "="*60)
    print("UNILABS API TESTS")
    print("="*60)
    
    results = []
    
    # 1. Login
    results.append(('Login', test_login_dev()))
    
    # 2. Academic Year
    results.append(('Academic Year', test_api_academic_year()[0]))
    
    # 3. Semesters
    success, semesters_data = test_api_semesters()
    results.append(('Semesters', success))
    
    if success and semesters_data.get('data'):
        # 4. Courses (χρησιμοποιούμε το πρώτο εξάμηνο)
        semester = semesters_data['data'][0]['id']
        success, courses_data = test_api_courses(semester)
        results.append(('Courses', success))
        
        if success and courses_data.get('data'):
            # 5. Labs
            course_id = courses_data['data'][0]['course_id']
            success, labs_data = test_api_labs(course_id)
            results.append(('Labs', success))
            
            if success and labs_data.get('data'):
                # 6. Groups
                lab_id = labs_data['data'][0]['lab_id']
                success, groups_data = test_api_groups(lab_id)
                results.append(('Groups', success))
                
                if success and groups_data.get('data'):
                    # 7. Enrollment Status
                    success, status_data = test_api_enrollment_status(lab_id)
                    results.append(('Enrollment Status', success))
                    
                    # 8. Group Professor
                    group_id = groups_data['data'][0]['group_id']
                    success, _ = test_api_group_professor(group_id)
                    results.append(('Group Professor', success))
                    
                    # 9. Register (μόνο αν δεν είναι ήδη εγγεγραμμένος)
                    if status_data.get('can_register'):
                        success, _ = test_api_register_lab(lab_id, group_id)
                        results.append(('Register Lab', success))
                        
                        # 10. Student Enrollments
                        success, enrollments_data = test_api_student_enrollments()
                        results.append(('Student Enrollments', success))
                        
                        # 11. Change Group (αν υπάρχει άλλο τμήμα)
                        if len(groups_data['data']) > 1:
                            new_group_id = groups_data['data'][1]['group_id']
                            success, _ = test_api_change_group(lab_id, group_id, new_group_id)
                            results.append(('Change Group', success))
                    else:
                        print("\n⚠️ Student already enrolled, skipping registration test")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = '✅' if result else '❌'
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    return passed == total

if __name__ == '__main__':
    print("Βεβαιωθείτε ότι το Flask server τρέχει στο localhost:5000")
    print("Εκτέλεση: cd thesis/unilabs/app && python app.py")
    input("Πατήστε Enter για να ξεκινήσει το testing...")
    
    run_all_tests()