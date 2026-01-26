-- Test data για το ακαδημαϊκό έτος 2025-2026
-- Εκτέλεση: Διαγραφή παλιών και εισαγωγή νέων δεδομένων

-- Ενημέρωση lab_groups με τρέχον έτος (2025)
UPDATE lab_groups SET year = 2025 WHERE group_id IN (1, 2, 3);
UPDATE lab_groups SET year = 2025 WHERE group_id = 4;

-- Ενημέρωση reg_limit για να είναι στο μέλλον
UPDATE course_lab SET reg_limit = '31/12/2025' WHERE lab_id = 1;
UPDATE course_lab SET reg_limit = '31/12/2025' WHERE lab_id = 2;

-- Προσθήκη περισσότερων εξαμήνων και μαθημάτων
INSERT OR IGNORE INTO coursename (course_id, name, description, semester) VALUES
(301, 'Δομές Δεδομένων', 'Εισαγωγή στις δομές δεδομένων', '3ο Εξάμηνο'),
(401, 'Βάσεις Δεδομένων', 'Σχεσιακές βάσεις και SQL', '4ο Εξάμηνο'),
(501, 'Λειτουργικά Συστήματα', 'Αρχιτεκτονική λειτουργικών συστημάτων', '5ο Εξάμηνο');

-- Προσθήκη εργαστηρίων για τα νέα μαθήματα
INSERT OR IGNORE INTO course_lab (lab_id, name, description, maxusers, reg_limit, max_misses) VALUES
(3, 'Εργαστήριο Δομών Δεδομένων', 'Υλοποίηση δομών σε C/C++', 20, '31/12/2025', 3),
(4, 'Εργαστήριο Βάσεων Δεδομένων', 'SQL και σχεδιασμός βάσεων', 18, '31/12/2025', 2),
(5, 'Εργαστήριο Λειτουργικών Συστημάτων', 'Linux και shell scripting', 15, '31/12/2025', 2);

-- Σύνδεση μαθημάτων με εργαστήρια
INSERT OR IGNORE INTO rel_course_lab (course_id, lab_id) VALUES
(301, 3),
(401, 4),
(501, 5);

-- Προσθήκη τμημάτων για τα νέα εργαστήρια
INSERT OR IGNORE INTO lab_groups (group_id, daytime, year, finalize) VALUES
(5, 'Δευτέρα, 14 - 16', 2025, ''),
(6, 'Τετάρτη, 10 - 12', 2025, ''),
(7, 'Πέμπτη, 10 - 12', 2025, ''),
(8, 'Πέμπτη, 14 - 16', 2025, ''),
(9, 'Παρασκευή, 10 - 12', 2025, ''),
(10, 'Παρασκευή, 12 - 14', 2025, '');

-- Σύνδεση εργαστηρίων με τμήματα
INSERT OR IGNORE INTO rel_lab_group (lab_id, group_id) VALUES
(3, 5),
(3, 6),
(4, 7),
(4, 8),
(5, 9),
(5, 10);

-- Σύνδεση καθηγητών με τμήματα
INSERT OR IGNORE INTO rel_group_prof (prof_id, group_id) VALUES
(1, 5),
(2, 6),
(1, 7),
(2, 8),
(1, 9),
(2, 10);

-- Καθαρισμός παλιών εγγραφών για τον test student (13628)
DELETE FROM rel_group_student WHERE am = 13628;
DELETE FROM rel_lab_student WHERE am = 13628;

-- Ενημέρωση email για τον test student
UPDATE student SET email = 'test.student@example.com' WHERE am = 13628;