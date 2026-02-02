"""
Ενημέρωση βάσης δεδομένων και εκτέλεση tests για το UniLabs
Εκτέλεση: python run_tests.py
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'labregister.sqlite')

def get_future_date(days=180):
    """Επιστρέφει μελλοντική ημερομηνία σε format DD/MM/YYYY"""
    future = datetime.now() + timedelta(days=days)
    return future.strftime("%d/%m/%Y")

def get_past_date(days=30):
    """Επιστρέφει παρελθοντική ημερομηνία σε format DD/MM/YYYY"""
    past = datetime.now() - timedelta(days=days)
    return past.strftime("%d/%m/%Y")

def get_current_year():
    """Επιστρέφει το τρέχον ακαδημαϊκό έτος"""
    today = datetime.now()
    if today.timetuple().tm_yday < 35:
        return today.year - 1
    return today.year

def update_database():
    """Ενημέρωση βάσης με δεδομένα για testing"""
    print("="*60)
    print("ΕΝΗΜΕΡΩΣΗ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ")
    print("="*60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        return False
    
    current_year = get_current_year()
    future_date = get_future_date(180)  # 6 μήνες μπροστά
    past_date = get_past_date(30)  # 1 μήνα πίσω
    
    print(f"📅 Current academic year: {current_year}")
    print(f"📅 Future reg_limit (open): {future_date}")
    print(f"📅 Past reg_limit (closed): {past_date}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 1. Ενημέρωση year σε όλα τα groups για το τρέχον ακαδημαϊκό έτος
        cursor.execute("UPDATE lab_groups SET year = ?", (current_year,))
        print(f"✅ Updated lab_groups year to {current_year} ({cursor.rowcount} rows)")
        
        # 2. Ενημέρωση ΟΛΩΝ των reg_limit σε μελλοντική ημερομηνία (ΑΝΟΙΧΤΕΣ ΕΓΓΡΑΦΕΣ)
        cursor.execute("UPDATE course_lab SET reg_limit = ?", (future_date,))
        print(f"✅ Updated ALL reg_limit to {future_date} (OPEN) ({cursor.rowcount} rows)")
        
        # 3. Ορισμός ΜΟΝΟ του lab_id=2 ως κλειστό (για testing closed registration)
        cursor.execute("UPDATE course_lab SET reg_limit = ? WHERE lab_id = 2", (past_date,))
        print(f"✅ Updated lab_id=2 reg_limit to {past_date} (CLOSED for testing)")
        
        # 4. Καθαρισμός εγγραφών του test student (13628)
        cursor.execute("DELETE FROM rel_group_student WHERE am = 13628")
        print(f"✅ Cleared rel_group_student for AM 13628 ({cursor.rowcount} rows)")
        
        cursor.execute("DELETE FROM rel_lab_student WHERE am = 13628")
        print(f"✅ Cleared rel_lab_student for AM 13628 ({cursor.rowcount} rows)")
        
        # 5. Ενημέρωση email για test student
        cursor.execute("UPDATE student SET email = 'test.student@example.com' WHERE am = 13628")
        print(f"✅ Updated email for AM 13628")
        
        # 6. Προσθήκη νέων εξαμήνων/μαθημάτων
        new_courses = [
            (301, 'Δομές Δεδομένων', 'Εισαγωγή στις δομές δεδομένων', '3ο Εξάμηνο'),
            (401, 'Βάσεις Δεδομένων', 'Σχεσιακές βάσεις και SQL', '4ο Εξάμηνο'),
            (501, 'Λειτουργικά Συστήματα', 'Αρχιτεκτονική λειτουργικών συστημάτων', '5ο Εξάμηνο'),
            (601, 'Δίκτυα Υπολογιστών', 'TCP/IP και δικτυακός προγραμματισμός', '6ο Εξάμηνο'),
        ]
        for course in new_courses:
            try:
                cursor.execute(
                    "INSERT INTO coursename (course_id, name, description, semester) VALUES (?, ?, ?, ?)",
                    course
                )
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified {len(new_courses)} courses")
        
        # 7. Προσθήκη νέων εργαστηρίων με ΜΕΛΛΟΝΤΙΚΗ reg_limit
        new_labs = [
            (3, 'Εργαστήριο Δομών Δεδομένων', 'Υλοποίηση δομών σε C/C++', 20, future_date, 3),
            (4, 'Εργαστήριο Βάσεων Δεδομένων', 'SQL και σχεδιασμός βάσεων', 18, future_date, 2),
            (5, 'Εργαστήριο Λειτουργικών Συστημάτων', 'Linux και shell scripting', 15, future_date, 2),
            (6, 'Εργαστήριο Δικτύων', 'Wireshark και socket programming', 12, future_date, 2),
        ]
        for lab in new_labs:
            try:
                cursor.execute(
                    "INSERT INTO course_lab (lab_id, name, description, maxusers, reg_limit, max_misses) VALUES (?, ?, ?, ?, ?, ?)",
                    lab
                )
            except sqlite3.IntegrityError:
                # Update existing with new reg_limit
                cursor.execute(
                    "UPDATE course_lab SET reg_limit = ? WHERE lab_id = ?",
                    (future_date, lab[0])
                )
        print(f"✅ Added/verified {len(new_labs)} labs with future reg_limit")
        
        # 8. Σύνδεση μαθημάτων με εργαστήρια
        course_lab_rels = [(301, 3), (401, 4), (501, 5), (601, 6)]
        for rel in course_lab_rels:
            try:
                cursor.execute("INSERT INTO rel_course_lab (course_id, lab_id) VALUES (?, ?)", rel)
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified course-lab relations")
        
        # 9. Προσθήκη νέων τμημάτων
        new_groups = [
            (5, 'Δευτέρα, 14 - 16', current_year, ''),
            (6, 'Τετάρτη, 10 - 12', current_year, ''),
            (7, 'Πέμπτη, 10 - 12', current_year, ''),
            (8, 'Πέμπτη, 14 - 16', current_year, ''),
            (9, 'Παρασκευή, 10 - 12', current_year, ''),
            (10, 'Παρασκευή, 12 - 14', current_year, ''),
            (11, 'Σάββατο, 10 - 12', current_year, ''),
            (12, 'Σάββατο, 12 - 14', current_year, ''),
        ]
        for group in new_groups:
            try:
                cursor.execute(
                    "INSERT INTO lab_groups (group_id, daytime, year, finalize) VALUES (?, ?, ?, ?)",
                    group
                )
            except sqlite3.IntegrityError:
                # Update year for existing groups
                cursor.execute(
                    "UPDATE lab_groups SET year = ? WHERE group_id = ?",
                    (current_year, group[0])
                )
        print(f"✅ Added/verified {len(new_groups)} groups for year {current_year}")
        
        # 10. Σύνδεση εργαστηρίων με τμήματα
        lab_group_rels = [
            (1, 1), (1, 3),      # Lab 1 (existing) -> Groups 1, 3
            (2, 2), (2, 4),      # Lab 2 (closed) -> Groups 2, 4
            (3, 5), (3, 6),      # Lab 3 -> Groups 5, 6
            (4, 7), (4, 8),      # Lab 4 -> Groups 7, 8
            (5, 9), (5, 10),     # Lab 5 -> Groups 9, 10
            (6, 11), (6, 12),    # Lab 6 -> Groups 11, 12
        ]
        for rel in lab_group_rels:
            try:
                cursor.execute("INSERT INTO rel_lab_group (lab_id, group_id) VALUES (?, ?)", rel)
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified lab-group relations")
        
        # 11. Σύνδεση καθηγητών με τμήματα
        prof_group_rels = [
            (1, 1), (1, 3), (1, 5), (1, 7), (1, 9), (1, 11),
            (2, 2), (2, 4), (2, 6), (2, 8), (2, 10), (2, 12)
        ]
        for rel in prof_group_rels:
            try:
                cursor.execute("INSERT INTO rel_group_prof (prof_id, group_id) VALUES (?, ?)", rel)
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Added/verified professor-group relations")
        
        # 12. Δημιουργία πλήρους τμήματος (group 11 με maxusers=12)
        cursor.execute("DELETE FROM rel_group_student WHERE group_id = 11")
        for i in range(12):
            am = 90000 + i
            try:
                cursor.execute(
                    "INSERT INTO student (am, name, semester, pwd, email) VALUES (?, ?, ?, ?, ?)",
                    (am, f'Test User {i}', 4, '', f'test{i}@example.com')
                )
            except sqlite3.IntegrityError:
                pass
            try:
                cursor.execute(
                    "INSERT INTO rel_group_student (am, group_id, group_reg_daymonth, group_reg_year) VALUES (?, ?, ?, ?)",
                    (am, 11, '1/1', current_year)
                )
            except sqlite3.IntegrityError:
                pass
        print(f"✅ Created full group (group_id=11) with 12 students")
        
        # 13. Δημιουργία φοιτητή με αποτυχία
        try:
            cursor.execute(
                "INSERT INTO student (am, name, semester, pwd, email) VALUES (?, ?, ?, ?, ?)",
                (88888, 'Failed Student', 5, '', 'failed@example.com')
            )
        except sqlite3.IntegrityError:
            pass
        cursor.execute("DELETE FROM rel_lab_student WHERE am = 88888")
        cursor.execute(
            "INSERT INTO rel_lab_student (am, lab_id, misses, grade, reg_month, reg_year, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (88888, 3, 0, 0, 9, current_year - 1, 'Αποτυχία')
        )
        print(f"✅ Created failed student (AM=88888) for re-registration test")
        
        # 14. Προσθήκη απουσιών για testing notifications
        cursor.execute("DELETE FROM student_misses_pergroup WHERE am IN (13628, 13526)")
        absences_data = [
            (13526, 1, '10/10/2025, 17/10/2025, 24/10/2025'),
        ]
        for am, group_id, misses in absences_data:
            cursor.execute(
                "INSERT INTO student_misses_pergroup (am, group_id, misses) VALUES (?, ?, ?)",
                (am, group_id, misses)
            )
        print(f"✅ Added absence records for notification testing")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Database updated successfully!")
        print(f"\n📋 SUMMARY:")
        print(f"   - Academic year: {current_year}")
        print(f"   - Open registration labs: 1, 3, 4, 5, 6 (until {future_date})")
        print(f"   - Closed registration lab: 2 (expired {past_date})")
        print(f"   - Full group: 11 (12/12 students)")
        print(f"   - Test student cleared: AM 13628")
        return True
        
    except Exception as e:
        print(f"❌ Database update failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_database():
    """Επαλήθευση δεδομένων βάσης"""
    print("\n" + "="*60)
    print("ΕΠΑΛΗΘΕΥΣΗ ΔΕΔΟΜΕΝΩΝ ΒΑΣΗΣ")
    print("="*60)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT semester FROM coursename ORDER BY semester")
        semesters = cursor.fetchall()
        print(f"📚 Semesters: {[s[0] for s in semesters]}")
        
        cursor.execute("SELECT COUNT(*) FROM coursename")
        count = cursor.fetchone()[0]
        print(f"📖 Courses: {count}")
        
        cursor.execute("SELECT lab_id, name, reg_limit FROM course_lab ORDER BY lab_id")
        labs = cursor.fetchall()
        print(f"🔬 Labs: {len(labs)}")
        today = datetime.now().strftime("%d/%m/%Y")
        for lab in labs:
            try:
                reg_date = datetime.strptime(lab[2], "%d/%m/%Y")
                is_open = reg_date > datetime.now()
                status = "✅ OPEN" if is_open else "❌ CLOSED"
            except:
                status = "⚠️ UNKNOWN"
            print(f"   - Lab {lab[0]}: {lab[1]} (until {lab[2]}) [{status}]")
        
        current_year = get_current_year()
        cursor.execute("""
            SELECT lg.group_id, lg.daytime, lg.year, 
                   COUNT(rgs.am) as enrolled,
                   COALESCE(cl.maxusers, 15) as max_users
            FROM lab_groups lg
            LEFT JOIN rel_lab_group rlg ON lg.group_id = rlg.group_id
            LEFT JOIN course_lab cl ON rlg.lab_id = cl.lab_id
            LEFT JOIN rel_group_student rgs ON lg.group_id = rgs.group_id
            WHERE lg.year = ?
            GROUP BY lg.group_id
            ORDER BY lg.group_id
        """, (current_year,))
        groups = cursor.fetchall()
        print(f"👥 Groups (year {current_year}): {len(groups)}")
        for g in groups:
            max_users = g[4] if g[4] else 15
            status = "🔴 FULL" if g[3] >= max_users else f"🟢 {g[3]}/{max_users}"
            print(f"   - Group {g[0]}: {g[1]} [{status}]")
        
        cursor.execute("SELECT am, name, email FROM student WHERE am = 13628")
        student = cursor.fetchone()
        if student:
            print(f"👤 Test student: AM={student[0]}, Name={student[1]}")
        
        cursor.execute("SELECT COUNT(*) FROM rel_lab_student WHERE am = 13628")
        count = cursor.fetchone()[0]
        print(f"📝 Test student enrollments: {count} (should be 0 for clean testing)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

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
        # =====================================================
        # AUTHENTICATION TESTS
        # =====================================================
        print("\n" + "-"*40)
        print("AUTHENTICATION TESTS")
        print("-"*40)
        
        response = session.get(f"{BASE_URL}/cas_callback?username=student1", allow_redirects=False)
        test("Student Login Redirect", response.status_code == 302)
        
        response = session.get(f"{BASE_URL}/dashboard")
        test("Student Dashboard Access", response.status_code == 200 and 'Dashboard' in response.text)
        
        session.get(f"{BASE_URL}/logout")
        
        response = session.get(f"{BASE_URL}/cas_callback?username=prof1", allow_redirects=False)
        test("Professor Login Redirect", response.status_code == 302)
        
        response = session.get(f"{BASE_URL}/dashboard")
        test("Professor Dashboard Access", response.status_code == 200)
        
        session.get(f"{BASE_URL}/logout")
        session.get(f"{BASE_URL}/cas_callback?username=student1")
        
        # =====================================================
        # CASCADING DATA TESTS
        # =====================================================
        print("\n" + "-"*40)
        print("CASCADING DATA TESTS")
        print("-"*40)
        
        current_year = get_current_year()
        response = session.get(f"{BASE_URL}/api/academic-year")
        data = response.json()
        test("Academic Year API", data.get('success') and data.get('academic_year') == current_year,
             f"Year: {data.get('academic_year')} (expected {current_year})")
        
        response = session.get(f"{BASE_URL}/api/semesters")
        data = response.json()
        semesters = data.get('data', [])
        test("Semesters API", data.get('success') and len(semesters) > 0,
             f"Found {len(semesters)} semesters")
        
        if semesters:
            semester_id = semesters[0]['id']
            response = session.get(f"{BASE_URL}/api/courses/{semester_id}")
            data = response.json()
            courses = data.get('data', [])
            test("Courses API", data.get('success'),
                 f"Found {len(courses)} courses for {semester_id}")
            
            if courses:
                course_id = courses[0]['course_id']
                response = session.get(f"{BASE_URL}/api/labs/{course_id}")
                data = response.json()
                labs = data.get('data', [])
                test("Labs API", data.get('success'),
                     f"Found {len(labs)} labs for course {course_id}")
                
                if labs:
                    lab_id = labs[0]['lab_id']
                    response = session.get(f"{BASE_URL}/api/groups/{lab_id}")
                    data = response.json()
                    groups = data.get('data', [])
                    test("Groups API", data.get('success'),
                         f"Found {len(groups)} groups, reg_open={data.get('registration_open')}")
        
        # =====================================================
        # REGISTRATION TESTS
        # =====================================================
        print("\n" + "-"*40)
        print("REGISTRATION TESTS")
        print("-"*40)
        
        # Test with lab 1 (should be open)
        lab_id = 1
        response = session.get(f"{BASE_URL}/api/groups/{lab_id}")
        groups_data = response.json()
        
        test("Lab 1 Registration Open", groups_data.get('registration_open') == True,
             f"reg_limit: {groups_data.get('reg_limit')}")
        
        response = session.get(f"{BASE_URL}/api/student/enrollment-status/{lab_id}")
        data = response.json()
        test("Enrollment Status API", data.get('success'),
             f"enrolled={data.get('is_enrolled')}, can_register={data.get('can_register')}")
        
        if groups_data.get('data') and data.get('can_register'):
            group_id = groups_data['data'][0]['group_id']
            
            response = session.post(
                f"{BASE_URL}/api/register-lab",
                json={'lab_id': lab_id, 'group_id': group_id}
            )
            reg_data = response.json()
            test("Register Lab API", reg_data.get('success'),
                 reg_data.get('message', ''))
            
            response = session.get(f"{BASE_URL}/api/student/enrollments")
            data = response.json()
            enrollments = data.get('data', [])
            test("Student Enrollments API", data.get('success') and len(enrollments) > 0,
                 f"Found {len(enrollments)} enrollments")
            
            if len(groups_data['data']) > 1:
                new_group_id = groups_data['data'][1]['group_id']
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
        
        # =====================================================
        # ERROR CASE TESTS
        # =====================================================
        print("\n" + "-"*40)
        print("ERROR CASE TESTS")
        print("-"*40)
        
        response = session.get(f"{BASE_URL}/api/groups/2")
        data = response.json()
        test("Closed Registration Detection (Lab 2)", 
             data.get('registration_open') == False,
             f"reg_open={data.get('registration_open')}, msg={data.get('registration_message')}")
        
        response = session.get(f"{BASE_URL}/api/groups/6")
        data = response.json()
        full_group = next((g for g in data.get('data', []) if g['group_id'] == 11), None)
        if full_group:
            test("Full Group Detection (Group 11)",
                 full_group['occupancy']['is_full'] == True,
                 f"occupancy: {full_group['occupancy']['current']}/{full_group['occupancy']['max']}")
        else:
            test("Full Group Detection (Group 11)", False, "Group 11 not found in lab 6")
        
        # =====================================================
        # PROFILE & NOTIFICATION TESTS
        # =====================================================
        print("\n" + "-"*40)
        print("PROFILE & NOTIFICATION TESTS")
        print("-"*40)
        
        response = session.get(f"{BASE_URL}/api/student/profile")
        data = response.json()
        test("Get Profile API", data.get('success'),
             f"AM: {data.get('data', {}).get('am')}")
        
        response = session.put(
            f"{BASE_URL}/api/student/profile",
            json={'email': 'updated@example.com'}
        )
        data = response.json()
        test("Update Profile API", data.get('success'),
             data.get('message', ''))
        
        response = session.get(f"{BASE_URL}/api/student/notifications")
        data = response.json()
        test("Notifications API", data.get('success'),
             f"Count: {data.get('count', 0)}")
        
        # =====================================================
        # PROFESSOR INFO TEST
        # =====================================================
        print("\n" + "-"*40)
        print("PROFESSOR INFO TEST")
        print("-"*40)
        
        response = session.get(f"{BASE_URL}/api/groups/1/professor")
        data = response.json()
        test("Group Professor API", 
             data.get('success') or response.status_code == 404,
             f"Professors: {len(data.get('data', []))}" if data.get('success') else "No professor assigned")
        
        # =====================================================
        # SUMMARY
        # =====================================================
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        for name, result in results:
            status = '✅' if result else '❌'
            print(f"  {status} {name}")
        
        percentage = (100 * passed // total) if total > 0 else 0
        print(f"\n📊 Total: {passed}/{total} passed ({percentage}%)")
        
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
    
    if not update_database():
        print("\n❌ Database update failed. Aborting tests.")
        return
    
    if not verify_database():
        print("\n❌ Database verification failed. Aborting tests.")
        return
    
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()
    
    if result != 0:
        print("\n⚠️ Flask server is not running!")
        print("Please start it in another terminal:")
        print("  cd thesis/unilabs/app")
        print("  python app.py")
        print("\nThen run this script again, or just refresh the browser.")
        print("\n✅ Database has been updated - you can test manually now!")
        return
    
    success = run_api_tests()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n⚠️ SOME TESTS FAILED - Check the output above")

if __name__ == '__main__':
    main()