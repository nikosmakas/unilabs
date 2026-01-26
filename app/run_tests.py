"""
Ενημέρωση βάσης δεδομένων και εκτέλεση tests για το UniLabs
Εκτέλεση: python run_tests.py
"""
import sqlite3
import os
import sys

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'labregister.sqlite')

def update_database():
    """Ενημέρωση βάσης με δεδομένα για το 2025"""
    print("="*60)
    print("ΕΝΗΜΕΡΩΣΗ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ")
    print("="*60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Ενημέρωση year σε όλα τα groups
        cursor.execute("UPDATE lab_groups SET year = 2025")
        print(f"✅ Updated lab_groups year to 2025 ({cursor.rowcount} rows)")
        
        # 2. Ενημέρωση reg_limit για να είναι στο μέλλον
        cursor.execute("UPDATE course_lab SET reg_limit = '31/12/2025'")
        print(f"✅ Updated reg_limit to 31/12/2025 ({cursor.rowcount} rows)")
        
        # 3. Καθαρισμός εγγραφών του test student (13628)
        cursor.execute("DELETE FROM rel_group_student WHERE am = 13628")
        print(f"✅ Cleared rel_group_student for AM 13628 ({cursor.rowcount} rows)")
        
        cursor.execute("DELETE FROM rel_lab_student WHERE am = 13628")
        print(f"✅ Cleared rel_lab_student for AM 13628 ({cursor.rowcount} rows)")
        
        # 4. Ενημέρωση email για test student
        cursor.execute("UPDATE student SET email = 'test.student@example.com' WHERE am = 13628")
        print(f"✅ Updated email for AM 13628")
        
        # 5. Προσθήκη νέων εξαμήνων/μαθημάτων αν δεν υπάρχουν
        new_courses = [
            (301, 'Δομές Δεδομένων', 'Εισαγωγή στις δομές δεδομένων', '3ο Εξάμηνο'),
            (401, 'Βάσεις Δεδομένων', 'Σχεσιακές βάσεις και SQL', '4ο Εξάμηνο'),
            (501, 'Λειτουργικά Συστήματα', 'Αρχιτεκτονική λειτουργικών συστημάτων', '5ο Εξάμηνο'),
        ]
        for course in new_courses:
            try:
                cursor.execute(
                    "INSERT INTO coursename (course_id, name, description, semester) VALUES (?, ?, ?, ?)",
                    course
                )
            except sqlite3.IntegrityError:
                pass  # Already exists
        print(f"✅ Added/verified new courses")
        
        # 6. Προσθήκη νέων εργαστηρίων
        new_labs = [
            (3, 'Εργαστήριο Δομών Δεδομένων', 'Υλοποίηση δομών σε C/C++', 20, '31/12/2025', 3),
            (4, 'Εργαστήριο Βάσεων Δεδομένων', 'SQL και σχεδιασμός βάσεων', 18, '31/12/2025', 2),
            (5, 'Εργαστήριο Λειτουργικών Συστημάτων', 'Linux και shell scripting', 15, '31/12/2025', 2),
        ]
        for lab in new_labs:
            try:
                cursor.execute(
                    "INSERT INTO course_lab (lab_id, name, description, maxusers, reg_limit, max_misses) VALUES (?, ?, ?, ?, ?, ?)",
                    lab
                )
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified new labs")
        
        # 7. Σύνδεση μαθημάτων με εργαστήρια
        course_lab_rels = [(301, 3), (401, 4), (501, 5)]
        for rel in course_lab_rels:
            try:
                cursor.execute("INSERT INTO rel_course_lab (course_id, lab_id) VALUES (?, ?)", rel)
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified course-lab relations")
        
        # 8. Προσθήκη νέων τμημάτων
        new_groups = [
            (5, 'Δευτέρα, 14 - 16', 2025, ''),
            (6, 'Τετάρτη, 10 - 12', 2025, ''),
            (7, 'Πέμπτη, 10 - 12', 2025, ''),
            (8, 'Πέμπτη, 14 - 16', 2025, ''),
            (9, 'Παρασκευή, 10 - 12', 2025, ''),
            (10, 'Παρασκευή, 12 - 14', 2025, ''),
        ]
        for group in new_groups:
            try:
                cursor.execute(
                    "INSERT INTO lab_groups (group_id, daytime, year, finalize) VALUES (?, ?, ?, ?)",
                    group
                )
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified new groups")
        
        # 9. Σύνδεση εργαστηρίων με τμήματα
        lab_group_rels = [(3, 5), (3, 6), (4, 7), (4, 8), (5, 9), (5, 10)]
        for rel in lab_group_rels:
            try:
                cursor.execute("INSERT INTO rel_lab_group (lab_id, group_id) VALUES (?, ?)", rel)
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified lab-group relations")
        
        # 10. Σύνδεση καθηγητών με τμήματα
        prof_group_rels = [(1, 5), (2, 6), (1, 7), (2, 8), (1, 9), (2, 10)]
        for rel in prof_group_rels:
            try:
                cursor.execute("INSERT INTO rel_group_prof (prof_id, group_id) VALUES (?, ?)", rel)
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified professor-group relations")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Database updated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database update failed: {e}")
        return False

def verify_database():
    """Επαλήθευση δεδομένων βάσης"""
    print("\n" + "="*60)
    print("ΕΠΑΛΗΘΕΥΣΗ ΔΕΔΟΜΕΝΩΝ ΒΑΣΗΣ")
    print("="*60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Έλεγχος semesters
        cursor.execute("SELECT DISTINCT semester FROM coursename ORDER BY semester")
        semesters = cursor.fetchall()
        print(f"📚 Semesters: {[s[0] for s in semesters]}")
        
        # Έλεγχος courses
        cursor.execute("SELECT COUNT(*) FROM coursename")
        count = cursor.fetchone()[0]
        print(f"📖 Courses: {count}")
        
        # Έλεγχος labs
        cursor.execute("SELECT lab_id, name, reg_limit FROM course_lab")
        labs = cursor.fetchall()
        print(f"🔬 Labs: {len(labs)}")
        for lab in labs:
            print(f"   - Lab {lab[0]}: {lab[1]} (reg_limit: {lab[2]})")
        
        # Έλεγχος groups με year 2025
        cursor.execute("SELECT COUNT(*) FROM lab_groups WHERE year = 2025")
        count = cursor.fetchone()[0]
        print(f"👥 Groups with year 2025: {count}")
        
        # Έλεγχος test student
        cursor.execute("SELECT am, name, email FROM student WHERE am = 13628")
        student = cursor.fetchone()
        if student:
            print(f"👤 Test student: AM={student[0]}, Name={student[1]}, Email={student[2]}")
        
        # Έλεγχος εγγραφών test student
        cursor.execute("SELECT COUNT(*) FROM rel_lab_student WHERE am = 13628")
        count = cursor.fetchone()[0]
        print(f"📝 Test student lab enrollments: {count}")
        
        cursor.execute("SELECT COUNT(*) FROM rel_group_student WHERE am = 13628")
        count = cursor.fetchone()[0]
        print(f"📝 Test student group enrollments: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def start_flask_server():
    """Έναρξη Flask server σε background"""
    import subprocess
    import time
    
    print("\n" + "="*60)
    print("ΕΚΚΙΝΗΣΗ FLASK SERVER")
    print("="*60)
    
    # Check if server is already running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()
    
    if result == 0:
        print("✅ Flask server already running on port 5000")
        return None
    
    # Start server
    print("Starting Flask server...")
    process = subprocess.Popen(
        [sys.executable, 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=BASE_DIR
    )
    
    # Wait for server to start
    time.sleep(3)
    
    # Check if running
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()
    
    if result == 0:
        print("✅ Flask server started successfully")
        return process
    else:
        print("❌ Failed to start Flask server")
        return None

def run_api_tests():
    """Εκτέλεση API tests"""
    import requests
    
    print("\n" + "="*60)
    print("ΕΚΤΕΛΕΣΗ API TESTS")
    print("="*60)
    
    BASE_URL = 'http://localhost:5000'
    session = requests.Session()
    results = []
    
    def test(name, condition, details=""):
        status = '✅ PASS' if condition else '❌ FAIL'
        results.append((name, condition))
        print(f"{status} - {name}")
        if details:
            print(f"      {details}")
        return condition
    
    try:
        # Test 1: Login
        print("\n--- Authentication Tests ---")
        response = session.get(f"{BASE_URL}/cas_callback?username=student1", allow_redirects=False)
        test("Dev Login Redirect", response.status_code == 302)
        
        response = session.get(f"{BASE_URL}/dashboard")
        test("Dashboard Access", response.status_code == 200 and 'Dashboard' in response.text)
        
        # Test 2: Academic Year
        print("\n--- Academic Year Test ---")
        response = session.get(f"{BASE_URL}/api/academic-year")
        data = response.json()
        test("Academic Year API", data.get('success') and data.get('academic_year') == 2025, 
             f"Year: {data.get('academic_year')}")
        
        # Test 3: Semesters
        print("\n--- Cascading Data Tests ---")
        response = session.get(f"{BASE_URL}/api/semesters")
        data = response.json()
        semesters = data.get('data', [])
        test("Semesters API", data.get('success') and len(semesters) > 0,
             f"Found {len(semesters)} semesters")
        
        if semesters:
            semester_id = semesters[0]['id']
            
            # Test 4: Courses
            response = session.get(f"{BASE_URL}/api/courses/{semester_id}")
            data = response.json()
            courses = data.get('data', [])
            test("Courses API", data.get('success'),
                 f"Found {len(courses)} courses for {semester_id}")
            
            if courses:
                course_id = courses[0]['course_id']
                
                # Test 5: Labs
                response = session.get(f"{BASE_URL}/api/labs/{course_id}")
                data = response.json()
                labs = data.get('data', [])
                test("Labs API", data.get('success'),
                     f"Found {len(labs)} labs for course {course_id}")
                
                if labs:
                    lab_id = labs[0]['lab_id']
                    
                    # Test 6: Groups
                    response = session.get(f"{BASE_URL}/api/groups/{lab_id}")
                    data = response.json()
                    groups = data.get('data', [])
                    test("Groups API", data.get('success'),
                         f"Found {len(groups)} groups, reg_open={data.get('registration_open')}")
                    
                    # Test 7: Enrollment Status
                    print("\n--- Registration Tests ---")
                    response = session.get(f"{BASE_URL}/api/student/enrollment-status/{lab_id}")
                    data = response.json()
                    test("Enrollment Status API", data.get('success'),
                         f"enrolled={data.get('is_enrolled')}, can_register={data.get('can_register')}")
                    
                    if groups and data.get('can_register'):
                        group_id = groups[0]['group_id']
                        
                        # Test 8: Register
                        response = session.post(
                            f"{BASE_URL}/api/register-lab",
                            json={'lab_id': lab_id, 'group_id': group_id}
                        )
                        data = response.json()
                        test("Register Lab API", data.get('success'),
                             data.get('message', ''))
                        
                        # Test 9: Student Enrollments
                        response = session.get(f"{BASE_URL}/api/student/enrollments")
                        data = response.json()
                        enrollments = data.get('data', [])
                        test("Student Enrollments API", data.get('success'),
                             f"Found {len(enrollments)} enrollments")
                        
                        # Test 10: Group Professor
                        response = session.get(f"{BASE_URL}/api/groups/{group_id}/professor")
                        data = response.json()
                        test("Group Professor API", data.get('success') or response.status_code == 404,
                             f"Professors: {len(data.get('data', []))}" if data.get('success') else "No professor assigned")
                        
                        # Test 11: Change Group (αν υπάρχει άλλο group)
                        if len(groups) > 1:
                            new_group_id = groups[1]['group_id']
                            response = session.put(
                                f"{BASE_URL}/api/change-group",
                                json={
                                    'lab_id': lab_id,
                                    'old_group_id': group_id,
                                    'new_group_id': new_group_id
                                }
                            )
                            data = response.json()
                            test("Change Group API", data.get('success'),
                                 data.get('message', ''))
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = '✅' if result else '❌'
            print(f"  {status} {name}")
        
        print(f"\n📊 Total: {passed}/{total} passed ({100*passed//total}%)")
        
        return passed == total
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Flask server. Make sure it's running on port 5000.")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("UNILABS TESTING SUITE")
    print("="*60)
    
    # Step 1: Update database
    if not update_database():
        print("\n❌ Database update failed. Aborting tests.")
        return
    
    # Step 2: Verify database
    if not verify_database():
        print("\n❌ Database verification failed. Aborting tests.")
        return
    
    # Step 3: Check if Flask is running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()
    
    if result != 0:
        print("\n⚠️ Flask server is not running!")
        print("Please start it in another terminal:")
        print("  cd thesis/unilabs/app")
        print("  python app.py")
        print("\nThen run this script again.")
        return
    
    # Step 4: Run API tests
    success = run_api_tests()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n⚠️ SOME TESTS FAILED - Check the output above")

if __name__ == '__main__':
    main()