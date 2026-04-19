from flask import Blueprint, render_template, session, redirect, request, url_for
from flask_babel import _

from models import (
    Student, Professor, db, LabGroup, CourseLab,
    RelLabGroup, RelLabStudent, StudentMissesPerGroup,
    Coursename, CourseEligibility, RelCourseLab
)
from auth import (
    require_permission, require_role, get_academic_year, get_student_enrollments
)
from helpers import get_group_occupancy

views_bp = Blueprint('views_bp', __name__)


@views_bp.route('/set-language/<lang>')
def set_language(lang):
    """Switch UI language between Greek and English."""
    if lang in ('el', 'en'):
        session['language'] = lang
    return redirect(request.referrer or url_for('views_bp.dashboard'))


@views_bp.route('/dashboard')
@require_permission('dashboard', 'view')
def dashboard():
    """Dashboard home - lightweight summary counts only."""
    academic_year = get_academic_year()

    lab_count = CourseLab.query.count()
    group_count = db.session.query(LabGroup).filter(LabGroup.year == academic_year).count()
    professor_count = Professor.query.count()

    return render_template('dashboard_home.html',
                           active_page='dashboard',
                           lab_count=lab_count,
                           group_count=group_count,
                           professor_count=professor_count)


@views_bp.route('/registration')
@require_permission('registrations', 'create')
def registration():
    """Student registration form - data loaded via API calls from JS."""
    return render_template('registration.html',
                           active_page='registration')


@views_bp.route('/my-enrollments')
@require_role('student')
def my_enrollments():
    """Current student enrollments."""
    academic_year = get_academic_year()
    student_am = session.get('schGrAcPersonID')
    student_enrollments = get_student_enrollments(student_am, academic_year) if student_am else []

    return render_template('my_enrollments.html',
                           active_page='my_enrollments',
                           student_enrollments=student_enrollments)


@views_bp.route('/labs')
@require_permission('dashboard', 'view')
def labs_page():
    """Labs listing."""
    labs = CourseLab.query.all()
    courses = Coursename.query.order_by(Coursename.semester, Coursename.name).all() if session.get('role') == 'admin' else []
    return render_template('labs.html',
                           active_page='labs',
                           labs=labs,
                           courses=courses)


@views_bp.route('/groups-view')
@require_permission('dashboard', 'view')
def groups_page():
    """Groups listing with occupancy."""
    academic_year = get_academic_year()

    groups_raw = db.session.query(
        LabGroup, RelLabGroup.lab_id, CourseLab.name.label('lab_name'),
        Coursename.semester.label('semester')
    ).join(
        RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
    ).join(
        CourseLab, RelLabGroup.lab_id == CourseLab.lab_id
    ).outerjoin(
        RelCourseLab, CourseLab.lab_id == RelCourseLab.lab_id
    ).outerjoin(
        Coursename, RelCourseLab.course_id == Coursename.course_id
    ).filter(LabGroup.year == academic_year).all()

    groups = []
    for group, lab_id, lab_name, semester in groups_raw:
        occupancy = get_group_occupancy(group.group_id, lab_id)
        groups.append({
            'group_id': group.group_id,
            'daytime': group.daytime,
            'year': group.year,
            'lab_id': lab_id,
            'lab_name': lab_name,
            'semester': semester or '-',
            'occupancy_percentage': occupancy['percentage'],
            'available_spots': occupancy['available'],
            'is_full': occupancy['is_full']
        })

    all_labs = []
    professors = []
    if session.get('role') == 'admin':
        all_labs = CourseLab.query.order_by(CourseLab.name).all()
        professors = Professor.query.order_by(Professor.name).all()

    return render_template('groups.html',
                           active_page='groups',
                           groups=groups,
                           all_labs=all_labs,
                           professors=professors)


@views_bp.route('/students-view')
@require_permission('students_list', 'view_professor_students')
def students_page():
    """Students listing (professors/admins only)."""
    students = Student.query.all()
    return render_template('students.html',
                           active_page='students',
                           students=students)


@views_bp.route('/professors-view')
@require_permission('professors_list', 'view')
def professors_page():
    """Professors listing."""
    professors = Professor.query.all()
    return render_template('professors.html',
                           active_page='professors',
                           professors=professors)


@views_bp.route('/registrations-view')
@require_permission('registrations', 'manage')
def registrations_page():
    """Registrations listing (professors/admins only)."""
    registrations_raw = RelLabStudent.query.all()
    registrations = []
    for reg in registrations_raw:
        lab = CourseLab.query.get(reg.lab_id)
        student = Student.query.get(reg.am)
        registrations.append({
            'am': reg.am,
            'student_name': student.name if student else 'Unknown',
            'lab_id': reg.lab_id,
            'lab_name': lab.name if lab else 'Unknown',
            'status': reg.status,
        })

    return render_template('registrations.html',
                           active_page='registrations',
                           registrations=registrations)


@views_bp.route('/absences-view')
@require_permission('absences', 'view_group')
def absences_page():
    """Absences listing (professors/admins only)."""
    absences_raw = StudentMissesPerGroup.query.all()
    absences = []
    for miss in absences_raw:
        student = Student.query.get(miss.am)
        absences.append({
            'am': miss.am,
            'student_name': student.name if student else 'Unknown',
            'group_id': miss.group_id,
            'misses': miss.misses,
        })
    return render_template('absences.html',
                           active_page='absences',
                           absences=absences)


@views_bp.route('/my-groups')
@require_permission('groups', 'view')
def my_groups_page():
    """Professor's groups - data loaded via API calls from JS."""
    return render_template('my_groups.html',
                           active_page='my_groups')


@views_bp.route('/admin/courses')
@require_permission('registrations', 'manage')
def admin_courses_page():
    """Admin course management - eligibility list uploads."""
    if session.get('role') != 'admin':
        from flask import abort
        abort(403)
    courses = Coursename.query.order_by(Coursename.semester, Coursename.name).all()
    courses_data = []
    for c in courses:
        count = CourseEligibility.query.filter_by(course_id=c.course_id).count()
        courses_data.append({
            'course_id': c.course_id,
            'name': c.name,
            'semester': c.semester,
            'eligible_count': count
        })
    return render_template('admin_courses.html',
                           active_page='admin_courses',
                           courses=courses_data)
