-- SQLite schema and data for labregister

-- Table: coursename
CREATE TABLE coursename (
  course_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  semester TEXT NOT NULL
);
INSERT INTO coursename (course_id, name, description, semester) VALUES
(201, 'Ψηφιακά Ηλεκτρονικά', '..να συμπληρωθεί', '2ο Εξάμηνο'),
(701, 'ΠΘ Προγραμματισμού Δικτύων', '..να συμπληρωθεί', '7ο Εξάμηνο');

-- Table: coursetoprof
CREATE TABLE coursetoprof (
  course_id INTEGER NOT NULL,
  prof_id INTEGER NOT NULL
);
INSERT INTO coursetoprof (course_id, prof_id) VALUES
(201, 1),
(201, 2);

-- Table: course_lab
CREATE TABLE course_lab (
  lab_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  maxusers INTEGER NOT NULL,
  reg_limit TEXT NOT NULL,
  max_misses INTEGER NOT NULL
);
INSERT INTO course_lab (lab_id, name, description, maxusers, reg_limit, max_misses) VALUES
(1, 'Εργαστήριο Ψηφιακών Ηλεκτρονικών', '..να συμπληρωθεί', 15, '07/10/2021', 2),
(2, 'Εργαστήριο ΠΘ Προγραμματισμού Δικτύων', '... να συμπληρωθεί', 10, '07/10/2021', 2);

-- Table: lab_groups
CREATE TABLE lab_groups (
  group_id INTEGER PRIMARY KEY AUTOINCREMENT,
  daytime TEXT NOT NULL,
  year INTEGER NOT NULL,
  finalize TEXT NOT NULL
);
INSERT INTO lab_groups (group_id, daytime, year, finalize) VALUES
(1, 'Δευτέρα, 10 - 12', 2021, ''),
(2, 'Τρίτη, 10 - 12', 2021, ''),
(3, 'Τρίτη, 12 - 14', 2021, ''),
(4, 'Τετάρτη, 12 - 14', 2011, '');

-- Table: professor
CREATE TABLE professor (
  prof_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  status TEXT NOT NULL,
  office TEXT NOT NULL,
  email TEXT NOT NULL,
  tel TEXT NOT NULL
);
INSERT INTO professor (prof_id, name, status, office, email, tel) VALUES
(1, 'Βαρτζιώτης Φώτης', 'Καθηγητής Εφαρμογών', 'Χώρος Γραφείων Καθηγητών', 'fvartzi@gmail.com', '2681050448'),
(2, 'test userprof', 'Καθηγητής Εφαρμογών', 'Χώρος Εργαστηρίου ', 'testuser@kati.com', '1243242354');

-- Table: rel_course_lab
CREATE TABLE rel_course_lab (
  course_id INTEGER NOT NULL,
  lab_id INTEGER NOT NULL
);
INSERT INTO rel_course_lab (course_id, lab_id) VALUES
(201, 1),
(701, 2);

-- Table: rel_group_prof
CREATE TABLE rel_group_prof (
  prof_id INTEGER NOT NULL,
  group_id INTEGER NOT NULL
);
INSERT INTO rel_group_prof (prof_id, group_id) VALUES
(1, 1),
(2, 1);

-- Table: rel_group_student
CREATE TABLE rel_group_student (
  am INTEGER NOT NULL,
  group_id INTEGER NOT NULL,
  group_reg_daymonth TEXT NOT NULL,
  group_reg_year INTEGER NOT NULL
);
INSERT INTO rel_group_student (am, group_id, group_reg_daymonth, group_reg_year) VALUES
(13628, 2, '5/3', 2012),
(9100, 3, '', 0),
(13526, 1, '', 0),
(13628, 1, '', 0),
(13526, 2, '', 0),
(13000, 2, '', 0),
(13001, 3, '', 0),
(13002, 2, '', 0),
(13003, 2, '', 0),
(13004, 4, '', 0),
(13004, 2, '', 0),
(13005, 2, '', 0),
(13006, 2, '', 0),
(13007, 2, '', 0),
(13008, 2, '', 0),
(13009, 2, '', 0),
(13628, 4, '', 0);

-- Table: rel_lab_group
CREATE TABLE rel_lab_group (
  lab_id INTEGER NOT NULL,
  group_id INTEGER NOT NULL
);
INSERT INTO rel_lab_group (lab_id, group_id) VALUES
(1, 1),
(2, 2),
(1, 3),
(2, 4);

-- Table: rel_lab_student
CREATE TABLE rel_lab_student (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  am INTEGER NOT NULL,
  lab_id INTEGER NOT NULL,
  misses INTEGER NOT NULL,
  grade INTEGER NOT NULL,
  reg_month INTEGER NOT NULL,
  reg_year INTEGER NOT NULL,
  status TEXT NOT NULL
);
INSERT INTO rel_lab_student (id, am, lab_id, misses, grade, reg_month, reg_year, status) VALUES
(1, 9100, 1, 1, 5, 5, 2012, 'Σε Εξέλιξη'),
(2, 13526, 1, 0, 0, 5, 2012, 'Αποτυχία'),
(4, 13628, 1, 0, 0, 5, 2012, 'Κατοχυρωμένο'),
(5, 13000, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(6, 13001, 1, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(7, 13002, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(8, 13003, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(9, 13004, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(12, 13005, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(13, 13006, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(14, 13007, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(15, 13008, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(16, 13009, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη'),
(17, 13010, 2, 0, 0, 5, 2012, 'Σε Εξέλιξη');

-- Table: student
CREATE TABLE student (
  am INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  semester INTEGER NOT NULL,
  pwd TEXT NOT NULL,
  email TEXT NOT NULL
);
INSERT INTO student (am, name, semester, pwd, email) VALUES
(9100, 'user test3', 7, 'byay1616BY', ''),
(12211, 'user test 2', 2, 'esuf2416ES', ''),
(12345, 'user test', 2, '12345', ''),
(13000, 'user test6', 7, 'syvn7568SY', ''),
(13001, 'user test7', 2, 'xszr8961XS', ''),
(13002, 'user test8', 7, 'pcwz6230PC', ''),
(13003, 'user test9', 7, 'alwn1212AL', ''),
(13004, 'user test10', 7, 'ghfy3148GH', ''),
(13005, 'user test11', 7, 'rwjf7144RW', ''),
(13006, 'user test12', 7, 'spvm7496SP', ''),
(13007, 'user test13', 7, 'xvgt9246XV', ''),
(13008, 'user test14', 7, 'htfn3446HT', ''),
(13009, 'user test14', 7, 'lens5137LE', ''),
(13010, 'user test15', 7, 'yeez9454YE', ''),
(13526, 'user test5', 1, 'yxqn9607YX', ''),
(13628, 'Βαρτζιώτης Ι. Φώτης', 2, '12345', '');

-- Table: student_misses_pergroup
CREATE TABLE student_misses_pergroup (
  am INTEGER NOT NULL,
  group_id INTEGER NOT NULL,
  misses TEXT NOT NULL
);
INSERT INTO student_misses_pergroup (am, group_id, misses) VALUES
(13628, 2, '04/04/2012'),
(13526, 1, '17/05/2012'),
(13526, 1, '7/05/2012'),
(13526, 1, '24/05/2012'),
(13002, 2, '24/05/2012'),
(13003, 2, '24/05/2012'),
(13006, 2, '24/05/2012'),
(13009, 2, '24/05/2012'); 