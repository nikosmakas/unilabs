from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Coursename(db.Model):
    __tablename__ = 'coursename'
    course_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    semester = db.Column(db.Text, nullable=False)

class Coursetoprof(db.Model):
    __tablename__ = 'coursetoprof'
    course_id = db.Column(db.Integer, primary_key=True)
    prof_id = db.Column(db.Integer, primary_key=True)

class CourseLab(db.Model):
    __tablename__ = 'course_lab'
    lab_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    maxusers = db.Column(db.Integer, nullable=False)
    reg_limit = db.Column(db.Text, nullable=False)
    max_misses = db.Column(db.Integer, nullable=False)

class LabGroup(db.Model):
    __tablename__ = 'lab_groups'
    group_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    daytime = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    finalize = db.Column(db.Text, nullable=False)

class Professor(db.Model):
    __tablename__ = 'professor'
    prof_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False)
    office = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    tel = db.Column(db.Text, nullable=False)

class RelCourseLab(db.Model):
    __tablename__ = 'rel_course_lab'
    course_id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, primary_key=True)

class RelGroupProf(db.Model):
    __tablename__ = 'rel_group_prof'
    prof_id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, primary_key=True)

class RelGroupStudent(db.Model):
    __tablename__ = 'rel_group_student'
    am = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, primary_key=True)
    group_reg_daymonth = db.Column(db.Text, nullable=False)
    group_reg_year = db.Column(db.Integer, nullable=False)

class RelLabGroup(db.Model):
    __tablename__ = 'rel_lab_group'
    lab_id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, primary_key=True)

class RelLabStudent(db.Model):
    __tablename__ = 'rel_lab_student'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    am = db.Column(db.Integer, nullable=False)
    lab_id = db.Column(db.Integer, nullable=False)
    misses = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    reg_month = db.Column(db.Integer, nullable=False)
    reg_year = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Text, nullable=False)

class Student(UserMixin, db.Model):
    __tablename__ = 'student'
    am = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    pwd = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)

    def get_id(self):
        return str(self.am)

    def check_password(self, password):
        return self.pwd == password

class StudentMissesPerGroup(db.Model):
    __tablename__ = 'student_misses_pergroup'
    am = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, primary_key=True)
    misses = db.Column(db.Text, nullable=False) 