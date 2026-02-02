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
            (501, 'Λειτουργικά Συστήματ