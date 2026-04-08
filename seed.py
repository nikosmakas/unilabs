# -*- coding: utf-8 -*-
"""
seed.py - Populate the UniLabs SQLite database with realistic mock data.

Usage:
    cd thesis/unilabs
    python seed.py

Idempotent: safe to run multiple times. Uses INSERT OR REPLACE / INSERT OR IGNORE.
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'app', 'data', 'labregister.sqlite')


def get_academic_year():
    today = datetime.now()
    return today.year - 1 if today.timetuple().tm_yday < 35 else today.year


def future_date(days=180):
    return (datetime.now() + timedelta(days=days)).strftime('%d/%m/%Y')


def past_date(days=30):
    return (datetime.now() - timedelta(days=days)).strftime('%d/%m/%Y')


def seed():
    if not os.path.exists(DB_PATH):
        print(f'ERROR: Database not found at {DB_PATH}')
        sys.exit(1)

    year = get_academic_year()
    open_limit = future_date(180)
    closed_limit = past_date(30)

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA foreign_keys = OFF')
    cur = conn.cursor()

    print('=' * 60)
    print('SEED: Populating UniLabs database')
    print(f'  Academic year : {year}')
    print(f'  Open reg limit: {open_limit}')
    print(f'  Closed limit  : {closed_limit}')
    print('=' * 60)

    # =================================================================
    # 1. PROFESSORS  (101, 102  +  admin row 999)
    # =================================================================
    professors = [
        (101, 'Παπαδόπουλος Νίκος',   'Αναπληρωτής Καθηγητής',
         'Γραφείο Α-201', 'npapadopoulos@uoi.gr', '2651007101'),
        (102, 'Αντωνίου Ελένη',        'Επίκουρη Καθηγήτρια',
         'Γραφείο Β-305', 'eantonioiu@uoi.gr',     '2651007102'),
        (999, 'System Administrator',   'Διαχειριστής',
         'IT Office',     'admin@uoi.gr',           '2651009999'),
    ]
    for p in professors:
        cur.execute(
            'INSERT OR REPLACE INTO professor '
            '(prof_id, name, status, office, email, tel) VALUES (?,?,?,?,?,?)', p)
    print(f'  Professors: {len(professors)} upserted (IDs 101, 102, 999)')

    # =================================================================
    # 2. SEMESTERS & COURSES  (2 semesters, 4 courses)
    # =================================================================
    courses = [
        (1001, 'Εισαγωγή στον Προγραμματισμό',
         'Βασικές αρχές προγραμματισμού σε Python', '3ο Εξάμηνο'),
        (1002, 'Δομές Δεδομένων',
         'Στοίβες, ουρές, δέντρα, γράφοι',         '3ο Εξάμηνο'),
        (1003, 'Βάσεις Δεδομένων',
         'Σχεσιακό μοντέλο, SQL, κανονικοποίηση',   '5ο Εξάμηνο'),
        (1004, 'Δίκτυα Υπολογιστών',
         'TCP/IP, socket programming, Wireshark',    '5ο Εξάμηνο'),
    ]
    for c in courses:
        cur.execute(
            'INSERT OR REPLACE INTO coursename '
            '(course_id, name, description, semester) VALUES (?,?,?,?)', c)
    print(f'  Courses   : {len(courses)} upserted (semesters 3, 5)')

    # Course-to-professor mapping
    course_prof = [
        (1001, 101), (1002, 101),
        (1003, 102), (1004, 102),
    ]
    for cp in course_prof:
        cur.execute('INSERT OR IGNORE INTO coursetoprof (course_id, prof_id) VALUES (?,?)', cp)

    # =================================================================
    # 3. LABS  (6 labs, lab 106 will be full, lab 102 closed registration)
    # =================================================================
    labs = [
        (101, 'Εργαστήριο Προγραμματισμού Ι',
         'Ασκήσεις Python', 20, open_limit, 3),
        (102, 'Εργαστήριο Προγραμματισμού ΙΙ',
         'Ασκήσεις C++',    15, closed_limit, 3),       # CLOSED
        (103, 'Εργαστήριο Δομών Δεδομένων',
         'Υλοποίηση δομών σε C', 20, open_limit, 3),
        (104, 'Εργαστήριο SQL',
         'Πρακτική σε PostgreSQL', 18, open_limit, 2),
        (105, 'Εργαστήριο Δικτύων',
         'Wireshark & sockets',   15, open_limit, 2),
        (106, 'Εργαστήριο Ασφάλειας Δικτύων',
         'Penetration testing basics', 3, open_limit, 2),  # max=3 ? will be FULL
    ]
    for lb in labs:
        cur.execute(
            'INSERT OR REPLACE INTO course_lab '
            '(lab_id, name, description, maxusers, reg_limit, max_misses) VALUES (?,?,?,?,?,?)', lb)
    print(f'  Labs      : {len(labs)} upserted  (102=closed, 106=will-be-full)')

    # Course ? Lab
    course_lab = [
        (1001, 101), (1001, 102),
        (1002, 103),
        (1003, 104),
        (1004, 105), (1004, 106),
    ]
    for cl in course_lab:
        cur.execute('INSERT OR IGNORE INTO rel_course_lab (course_id, lab_id) VALUES (?,?)', cl)

    # =================================================================
    # 4. GROUPS  (12 groups, 2 per lab)
    # =================================================================
    groups = [
        (201, 'Δευτέρα 10:00-12:00',    year, ''),
        (202, 'Τρίτη 14:00-16:00',      year, ''),
        (203, 'Τετάρτη 10:00-12:00',    year, ''),
        (204, 'Τετάρτη 14:00-16:00',    year, ''),
        (205, 'Πέμπτη 10:00-12:00',     year, ''),
        (206, 'Πέμπτη 14:00-16:00',     year, ''),
        (207, 'Παρασκευή 10:00-12:00',  year, ''),
        (208, 'Παρασκευή 14:00-16:00',  year, ''),
        (209, 'Δευτέρα 14:00-16:00',    year, ''),
        (210, 'Τρίτη 10:00-12:00',      year, ''),
        (211, 'Σάββατο 10:00-12:00',    year, ''),   # lab 106 group A
        (212, 'Σάββατο 12:00-14:00',    year, ''),   # lab 106 group B (full)
    ]
    for g in groups:
        cur.execute(
            'INSERT OR REPLACE INTO lab_groups '
            '(group_id, daytime, year, finalize) VALUES (?,?,?,?)', g)
    print(f'  Groups    : {len(groups)} upserted  (year={year})')

    # Lab ? Group
    lab_group = [
        (101, 201), (101, 202),
        (102, 203), (102, 204),
        (103, 205), (103, 206),
        (104, 207), (104, 208),
        (105, 209), (105, 210),
        (106, 211), (106, 212),
    ]
    for lg in lab_group:
        cur.execute('INSERT OR IGNORE INTO rel_lab_group (lab_id, group_id) VALUES (?,?)', lg)

    # Professor ? Group  (prof 101 owns semester-3 groups, prof 102 owns semester-5)
    prof_group = [
        (101, 201), (101, 202), (101, 203), (101, 204),
        (101, 205), (101, 206),
        (102, 207), (102, 208), (102, 209), (102, 210),
        (102, 211), (102, 212),
    ]
    for pg in prof_group:
        cur.execute('INSERT OR IGNORE INTO rel_group_prof (prof_id, group_id) VALUES (?,?)', pg)

    # =================================================================
    # 5. STUDENTS  (10 students, 5-digit IDs)
    # =================================================================
    students = [
        (10001, 'Αλεξίου Μαρία',       3, 'malexiou@student.uoi.gr'),
        (10002, 'Βασιλείου Γιώργος',    3, 'gvasileiou@student.uoi.gr'),
        (10003, 'Γεωργίου Ελένη',       5, 'egeorgiou@student.uoi.gr'),
        (10004, 'Δημητρίου Κώστας',     5, 'kdimitriou@student.uoi.gr'),
        (10005, 'Ευαγγέλου Σοφία',      3, 'sevangelou@student.uoi.gr'),
        (10006, 'Ζαχαρίου Πέτρος',      5, 'pzachariou@student.uoi.gr'),
        (10007, 'Ηλιόπουλος Ανδρέας',   3, 'ailiopoulos@student.uoi.gr'),
        (10008, 'Θεοδώρου Αικατερίνη',  5, 'atheodorou@student.uoi.gr'),
        (10009, 'Ιωάννου Δημήτρης',     7, 'dioannou@student.uoi.gr'),
        (10010, 'Καραγιάννης Νίκος',    7, 'nkaragiannis@student.uoi.gr'),
    ]
    # Also keep the legacy test student
    students.append((13628, 'Test Student (Dev)', 5, 'test.student@example.com'))

    for s in students:
        cur.execute(
            'INSERT OR REPLACE INTO student '
            '(am, name, semester, pwd, email) VALUES (?,?,?,?,?)',
            (s[0], s[1], s[2], '', s[3]))
    print(f'  Students  : {len(students)} upserted  (10001-10010 + 13628)')

    # =================================================================
    # 6. ENROLLMENTS  (varied: active, completed, failed)
    # =================================================================
    # Clear seed-created enrollments first to be idempotent
    seed_ams = [s[0] for s in students]
    placeholders = ','.join('?' * len(seed_ams))
    cur.execute(f'DELETE FROM rel_lab_student  WHERE am IN ({placeholders})', seed_ams)
    cur.execute(f'DELETE FROM rel_group_student WHERE am IN ({placeholders})', seed_ams)
    cur.execute(f'DELETE FROM student_misses_pergroup WHERE am IN ({placeholders})', seed_ams)

    in_progress = 'Σε Εξέλιξη'
    completed   = 'Ολοκληρωμένο'
    failed      = 'Αποτυχία'

    # (am, lab_id, group_id, status, misses_count, grade)
    enrollments = [
        # --- Lab 101 (Prog I) : 5 students active ---
        (10001, 101, 201, in_progress, 0, 0),
        (10002, 101, 201, in_progress, 0, 0),
        (10005, 101, 202, in_progress, 0, 0),
        (10007, 101, 202, in_progress, 0, 0),
        (13628, 101, 201, in_progress, 0, 0),   # dev student enrolled here
        # --- Lab 103 (Data Structures) : some active ---
        (10001, 103, 205, in_progress, 0, 0),
        (10002, 103, 206, in_progress, 0, 0),
        # --- Lab 104 (SQL) : completed + failed ---
        (10003, 104, 207, completed,   1, 7),
        (10004, 104, 208, in_progress, 0, 0),
        (10006, 104, 207, failed,      0, 3),    # failed, can re-register
        # --- Lab 105 (Networks) : active ---
        (10003, 105, 209, in_progress, 0, 0),
        (10008, 105, 210, in_progress, 0, 0),
        # --- Lab 106 (Security, max=3) : FILL group 212 to capacity ---
        (10003, 106, 212, in_progress, 0, 0),
        (10004, 106, 212, in_progress, 0, 0),
        (10006, 106, 212, in_progress, 0, 0),    # 3/3 ? FULL
    ]

    month_now = datetime.now().month
    year_now  = datetime.now().year

    for am, lab_id, group_id, status, misses, grade in enrollments:
        cur.execute(
            'INSERT INTO rel_lab_student '
            '(am, lab_id, misses, grade, reg_month, reg_year, status) '
            'VALUES (?,?,?,?,?,?,?)',
            (am, lab_id, misses, grade, month_now, year_now, status))
        cur.execute(
            'INSERT INTO rel_group_student '
            '(am, group_id, group_reg_daymonth, group_reg_year) VALUES (?,?,?,?)',
            (am, group_id, f'{datetime.now().day}/{month_now}', year_now))
    print(f'  Enrollments: {len(enrollments)} created')

    # =================================================================
    # 7. ABSENCES
    # =================================================================
    absences = [
        (10001, 201, '7/10/2025, 14/10/2025'),            # 2 absences in Prog I
        (10007, 202, '7/10/2025, 14/10/2025, 21/10/2025'),# 3 absences ? critical
        (10003, 209, '3/11/2025'),                          # 1 absence in Networks
        (13628, 201, '7/10/2025'),                          # dev student has 1 absence
    ]
    for am, gid, misses in absences:
        cur.execute(
            'INSERT OR REPLACE INTO student_misses_pergroup '
            '(am, group_id, misses) VALUES (?,?,?)', (am, gid, misses))
    print(f'  Absences  : {len(absences)} records')

    # =================================================================
    # COMMIT
    # =================================================================
    conn.commit()
    conn.close()

    print()
    print('=' * 60)
    print('SEED COMPLETE')
    print('=' * 60)
    print()
    print('Test accounts for FAKE_USERS / dev login:')
    print('  student1  ? AM 13628   (role: student)')
    print('  student2  ? AM 10001   (role: student)')
    print('  prof1     ? ID 101     (role: professor)')
    print('  prof2     ? ID 102     (role: professor)')
    print('  admin1    ? ID 999     (role: admin)')
    print()
    print('Edge-case data created:')
    print(f'  Lab 102 registration CLOSED  (expired {closed_limit})')
    print(f'  Lab 106 / Group 212 is FULL  (3/3 students)')
    print(f'  Student 10006 FAILED lab 104 (can re-register)')
    print(f'  Student 10007 has 3 absences (critical warning)')
    print(f'  Student 13628 enrolled in lab 101 + 1 absence')


if __name__ == '__main__':
    seed()
