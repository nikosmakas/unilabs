from flask import Blueprint, request, session, jsonify, Response
from datetime import datetime
import csv
import io

from models import (
    Student, Professor, db, LabGroup, CourseLab, RelGroupStudent,
    Coursename, RelCourseLab, RelLabGroup, RelLabStudent,
    StudentMissesPerGroup, RelGroupProf, CourseEligibility
)
from auth import (
    require_permission, audit_log, mask_pii,
    transactional_enrollment, record_absence,
    get_academic_year, validate_registration_period,
    get_student_lab_status,
    register_student_to_lab, change_student_group, get_student_enrollments,
    STATUS_FAILED, STATUS_IN_PROGRESS, STATUS_COMPLETED
)
from helpers import get_group_occupancy, get_student_notifications

api_bp = Blueprint('api_bp', __name__)


def _check_eligibility(student_am, lab_id):
    """Check if an eligibility list exists for the lab's course and whether
    the student is on it.  Returns (ok, message).
    """
    course_rel = RelCourseLab.query.filter_by(lab_id=lab_id).first()
    if not course_rel:
        return True, ''  # no course link → skip check
    course_id = course_rel.course_id
    # If no eligibility records uploaded for this course, allow everyone
    if not CourseEligibility.query.filter_by(course_id=course_id).first():
        return True, ''
    # Records exist – student must be on the list
    if CourseEligibility.query.filter_by(course_id=course_id, am=int(student_am)).first():
        return True, ''
    return False, '\u0394\u03b5\u03bd \u03ad\u03c7\u03b5\u03c4\u03b5 \u03b4\u03b9\u03ba\u03b1\u03af\u03c9\u03bc\u03b1 \u03b5\u03b3\u03b3\u03c1\u03b1\u03c6\u03ae\u03c2. \u0394\u03b5\u03bd \u03b2\u03c1\u03ad\u03b8\u03b7\u03ba\u03b5 \u03b4\u03ae\u03bb\u03c9\u03c3\u03b7 \u03c4\u03bf\u03c5 \u03b8\u03b5\u03c9\u03c1\u03b7\u03c4\u03b9\u03ba\u03bf\u03cd \u03bc\u03b1\u03b8\u03ae\u03bc\u03b1\u03c4\u03bf\u03c2.'


# =============================================================================
# CASCADING DATA APIs
# =============================================================================

@api_bp.route('/api/semesters')
@require_permission('dashboard', 'view')
def get_semesters():
    semesters = db.session.query(Coursename.semester).distinct().order_by(Coursename.semester).all()
    return jsonify({
        'success': True,
        'data': [{'id': s.semester, 'name': f'{s.semester}'} for s in semesters]
    })


@api_bp.route('/api/courses/<semester>')
@require_permission('dashboard', 'view')
def get_courses_by_semester(semester):
    courses = Coursename.query.filter_by(semester=semester).all()
    return jsonify({
        'success': True,
        'semester': semester,
        'data': [{
            'course_id': c.course_id,
            'name': c.name,
            'description': c.description
        } for c in courses]
    })


@api_bp.route('/api/labs/<int:course_id>')
@require_permission('dashboard', 'view')
def get_labs_by_course(course_id):
    labs = db.session.query(CourseLab).join(
        RelCourseLab, CourseLab.lab_id == RelCourseLab.lab_id
    ).filter(RelCourseLab.course_id == course_id).all()
    return jsonify({
        'success': True,
        'course_id': course_id,
        'data': [{
            'lab_id': lab.lab_id,
            'name': lab.name,
            'description': lab.description,
            'maxusers': lab.maxusers,
            'reg_limit': lab.reg_limit,
            'max_misses': lab.max_misses
        } for lab in labs]
    })


@api_bp.route('/api/groups/<int:lab_id>')
@require_permission('dashboard', 'view')
def get_groups_by_lab(lab_id):
    year = request.args.get('year', type=int, default=get_academic_year())

    groups = db.session.query(LabGroup).join(
        RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
    ).filter(
        RelLabGroup.lab_id == lab_id,
        LabGroup.year == year
    ).all()

    groups_data = []
    for group in groups:
        occupancy = get_group_occupancy(group.group_id, lab_id)
        groups_data.append({
            'group_id': group.group_id,
            'daytime': group.daytime,
            'year': group.year,
            'finalize': group.finalize,
            'occupancy': occupancy
        })

    lab = CourseLab.query.get(lab_id)
    period_valid, period_msg = validate_registration_period(lab_id)

    return jsonify({
        'success': True,
        'lab_id': lab_id,
        'lab_name': lab.name if lab else None,
        'reg_limit': lab.reg_limit if lab else None,
        'registration_open': period_valid,
        'registration_message': period_msg,
        'academic_year': year,
        'data': groups_data
    })


@api_bp.route('/api/academic-year')
@require_permission('dashboard', 'view')
def get_current_academic_year():
    return jsonify({
        'success': True,
        'academic_year': get_academic_year(),
        'calculated_at': datetime.now().isoformat()
    })


# =============================================================================
# REGISTRATION APIs
# =============================================================================

@api_bp.route('/api/register-lab', methods=['POST'])
@require_permission('registrations', 'create')
def api_register_lab():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    lab_id = data.get('lab_id')
    group_id = data.get('group_id')
    if not lab_id or not group_id:
        return jsonify({'success': False, 'message': 'Select a group'}), 400

    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    eligible, elig_msg = _check_eligibility(student_am, lab_id)
    if not eligible:
        return jsonify({'success': False, 'message': elig_msg}), 403

    success, message, details = register_student_to_lab(student_am, lab_id, group_id)
    status_code = 200 if success else 400
    return jsonify({'success': success, 'message': message, 'details': details}), status_code


@api_bp.route('/api/change-group', methods=['PUT'])
@require_permission('registrations', 'create')
def api_change_group():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    lab_id = data.get('lab_id')
    old_group_id = data.get('old_group_id')
    new_group_id = data.get('new_group_id')

    if not all([lab_id, old_group_id, new_group_id]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    if old_group_id == new_group_id:
        return jsonify({'success': False, 'message': 'Select a different group'}), 400

    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    eligible, elig_msg = _check_eligibility(student_am, lab_id)
    if not eligible:
        return jsonify({'success': False, 'message': elig_msg}), 403

    success, message, details = change_student_group(student_am, old_group_id, new_group_id, lab_id)
    status_code = 200 if success else 400
    return jsonify({'success': success, 'message': message, 'details': details}), status_code


@api_bp.route('/api/student/enrollments')
@require_permission('registrations', 'view')
def api_student_enrollments():
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    year = request.args.get('year', type=int, default=get_academic_year())
    enrollments = get_student_enrollments(student_am, year)
    return jsonify({'success': True, 'academic_year': year, 'data': enrollments})


@api_bp.route('/api/student/enrollment-status/<int:lab_id>')
@require_permission('registrations', 'view')
def api_enrollment_status(lab_id):
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    academic_year = get_academic_year()
    lab_status = get_student_lab_status(student_am, lab_id)

    current_group = db.session.query(RelGroupStudent, LabGroup).join(
        LabGroup, RelGroupStudent.group_id == LabGroup.group_id
    ).join(
        RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
    ).filter(
        RelGroupStudent.am == student_am,
        RelLabGroup.lab_id == lab_id,
        LabGroup.year == academic_year
    ).first()

    period_valid, period_msg = validate_registration_period(lab_id)

    return jsonify({
        'success': True,
        'lab_id': lab_id,
        'is_enrolled': lab_status is not None,
        'lab_status': lab_status,
        'current_group': {
            'group_id': current_group[0].group_id,
            'daytime': current_group[1].daytime
        } if current_group else None,
        'can_register': period_valid and (lab_status is None or lab_status.get('status') == STATUS_FAILED),
        'can_change_group': period_valid and current_group is not None,
        'registration_open': period_valid,
        'registration_message': period_msg
    })


@api_bp.route('/api/groups/<int:group_id>/professor')
@require_permission('professors_list', 'view')
def api_group_professor(group_id):
    professors = db.session.query(Professor).join(
        RelGroupProf, Professor.prof_id == RelGroupProf.prof_id
    ).filter(RelGroupProf.group_id == group_id).all()

    if not professors:
        return jsonify({'success': False, 'message': 'No professor found'}), 404

    return jsonify({
        'success': True,
        'data': [{
            'prof_id': p.prof_id,
            'name': p.name,
            'status': p.status,
            'office': p.office,
            'email': p.email,
            'tel': p.tel
        } for p in professors]
    })


@api_bp.route('/api/professor/my-groups')
@require_permission('groups', 'view')
def api_professor_groups():
    if session.get('role') not in ['professor', 'admin']:
        return jsonify({'success': False, 'message': 'Professors only'}), 403

    prof_id = session.get('schGrAcPersonID')
    academic_year = get_academic_year()

    groups = db.session.query(
        LabGroup, CourseLab.name.label('lab_name'), CourseLab.lab_id
    ).join(
        RelGroupProf, LabGroup.group_id == RelGroupProf.group_id
    ).join(
        RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
    ).join(
        CourseLab, RelLabGroup.lab_id == CourseLab.lab_id
    ).filter(
        RelGroupProf.prof_id == prof_id,
        LabGroup.year == academic_year
    ).all()

    result = []
    for group, lab_name, lab_id in groups:
        occupancy = get_group_occupancy(group.group_id, lab_id)
        result.append({
            'group_id': group.group_id,
            'daytime': group.daytime,
            'lab_name': lab_name,
            'lab_id': lab_id,
            'year': group.year,
            'occupancy': occupancy
        })

    return jsonify({'success': True, 'data': result})


@api_bp.route('/api/professor/group/<int:group_id>/students')
@require_permission('students_list', 'view_professor_students')
def api_professor_group_students(group_id):
    if session.get('role') not in ['professor', 'admin']:
        return jsonify({'success': False, 'message': 'Professors only'}), 403

    prof_id = session.get('schGrAcPersonID')

    if session.get('role') == 'professor':
        ownership = RelGroupProf.query.filter_by(
            prof_id=prof_id, group_id=group_id
        ).first()
        if not ownership:
            return jsonify({'success': False, 'message': 'Access denied'}), 403

    # Find the lab_id for this group
    lab_rel = RelLabGroup.query.filter_by(group_id=group_id).first()
    lab_id = lab_rel.lab_id if lab_rel else None

    students = db.session.query(Student).join(
        RelGroupStudent, Student.am == RelGroupStudent.am
    ).filter(RelGroupStudent.group_id == group_id).all()

    result = []
    for student in students:
        absence_rec = StudentMissesPerGroup.query.filter_by(
            am=student.am, group_id=group_id
        ).first()

        raw_misses = absence_rec.misses if absence_rec else ''
        if raw_misses:
            absences_list = [d.strip() for d in raw_misses.split(',') if d.strip()]
        else:
            absences_list = []

        grade = 0
        status = STATUS_IN_PROGRESS
        if lab_id:
            lab_enroll = RelLabStudent.query.filter_by(
                am=student.am, lab_id=lab_id
            ).first()
            if lab_enroll:
                grade = lab_enroll.grade
                status = lab_enroll.status

        result.append({
            'am': student.am,
            'name': student.name,
            'email': student.email,
            'semester': student.semester,
            'absences': raw_misses if raw_misses else '-',
            'absences_list': absences_list,
            'absences_count': len(absences_list),
            'grade': grade,
            'status': status
        })

    result.sort(key=lambda x: x['name'])
    return jsonify({'success': True, 'group_id': group_id, 'count': len(result), 'data': result})


@api_bp.route('/api/professor/group/<int:group_id>/student/<int:am>/grade', methods=['PUT'])
@require_permission('registrations', 'manage')
def api_update_student_grade(group_id, am):
    """Update a student's grade and auto-set status."""
    if session.get('role') not in ['professor', 'admin']:
        return jsonify({'success': False, 'message': 'Professors only'}), 403

    if session.get('role') == 'professor':
        ownership = RelGroupProf.query.filter_by(
            prof_id=session.get('schGrAcPersonID'), group_id=group_id
        ).first()
        if not ownership:
            return jsonify({'success': False, 'message': 'Access denied'}), 403

    data = request.get_json()
    if data is None or 'grade' not in data:
        return jsonify({'success': False, 'message': 'Grade is required'}), 400

    try:
        grade = int(data['grade'])
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Grade must be a number'}), 400

    if grade < 0 or grade > 10:
        return jsonify({'success': False, 'message': 'Grade must be between 0 and 10'}), 400

    lab_rel = RelLabGroup.query.filter_by(group_id=group_id).first()
    if not lab_rel:
        return jsonify({'success': False, 'message': 'Lab not found for this group'}), 404

    lab_enroll = RelLabStudent.query.filter_by(am=am, lab_id=lab_rel.lab_id).first()
    if not lab_enroll:
        return jsonify({'success': False, 'message': 'Student not enrolled in this lab'}), 404

    old_grade = lab_enroll.grade
    old_status = lab_enroll.status

    lab_enroll.grade = grade
    if grade >= 5:
        lab_enroll.status = STATUS_COMPLETED
    elif grade > 0:
        lab_enroll.status = STATUS_FAILED
    else:
        lab_enroll.status = STATUS_IN_PROGRESS

    db.session.commit()

    audit_log('grade_updated',
              old_value=f"grade={old_grade}, status={old_status}",
              new_value=f"grade={lab_enroll.grade}, status={lab_enroll.status}",
              reason=f"Grade set for student {am} in group {group_id}")

    return jsonify({
        'success': True,
        'message': 'Grade updated',
        'data': {
            'am': am,
            'grade': lab_enroll.grade,
            'status': lab_enroll.status
        }
    })


# =============================================================================
# ABSENCE MANAGEMENT APIs
# =============================================================================

def _check_group_ownership(group_id):
    """Verify the caller is professor-owner of this group, or admin. Returns error tuple or None."""
    if session.get('role') not in ['professor', 'admin']:
        return jsonify({'success': False, 'message': 'Professors only'}), 403
    if session.get('role') == 'professor':
        if not RelGroupProf.query.filter_by(
            prof_id=session.get('schGrAcPersonID'), group_id=group_id
        ).first():
            return jsonify({'success': False, 'message': 'Access denied'}), 403
    return None


@api_bp.route('/api/professor/group/<int:group_id>/student/<int:am>/absence', methods=['POST'])
@require_permission('absences', 'edit_group_absences')
def api_add_absence(group_id, am):
    """Add an absence date for a student in a group."""
    err = _check_group_ownership(group_id)
    if err:
        return err

    data = request.get_json() or {}
    date_str = data.get('date', '').strip()
    if not date_str:
        date_str = datetime.now().strftime('%d/%m/%Y')

    # Verify the student is actually in this group
    if not RelGroupStudent.query.filter_by(am=am, group_id=group_id).first():
        return jsonify({'success': False, 'message': 'Student not in this group'}), 404

    try:
        rec = StudentMissesPerGroup.query.filter_by(am=am, group_id=group_id).first()
        if rec:
            existing = [d.strip() for d in rec.misses.split(',') if d.strip()]
            if date_str in existing:
                return jsonify({'success': False, 'message': 'Absence already recorded for this date'}), 400
            existing.append(date_str)
            rec.misses = ', '.join(existing)
        else:
            rec = StudentMissesPerGroup(am=am, group_id=group_id, misses=date_str)
            db.session.add(rec)

        db.session.commit()

        absences_list = [d.strip() for d in rec.misses.split(',') if d.strip()]

        audit_log('absence_added',
                  new_value=f"Student {am} group {group_id}: {date_str}",
                  reason='Professor recorded absence')

        return jsonify({
            'success': True,
            'message': 'Absence recorded',
            'data': {
                'am': am,
                'date': date_str,
                'absences_list': absences_list,
                'absences_count': len(absences_list)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to record absence'}), 500


@api_bp.route('/api/professor/group/<int:group_id>/student/<int:am>/absence', methods=['DELETE'])
@require_permission('absences', 'edit_group_absences')
def api_remove_absence(group_id, am):
    """Remove a specific absence date for a student in a group."""
    err = _check_group_ownership(group_id)
    if err:
        return err

    data = request.get_json()
    if not data or not data.get('date', '').strip():
        return jsonify({'success': False, 'message': 'Date is required'}), 400

    date_str = data['date'].strip()

    try:
        rec = StudentMissesPerGroup.query.filter_by(am=am, group_id=group_id).first()
        if not rec:
            return jsonify({'success': False, 'message': 'No absences found'}), 404

        existing = [d.strip() for d in rec.misses.split(',') if d.strip()]
        if date_str not in existing:
            return jsonify({'success': False, 'message': 'Date not found in absences'}), 404

        existing.remove(date_str)

        if existing:
            rec.misses = ', '.join(existing)
        else:
            db.session.delete(rec)

        db.session.commit()

        audit_log('absence_removed',
                  old_value=f"Student {am} group {group_id}: {date_str}",
                  reason='Professor removed absence')

        return jsonify({
            'success': True,
            'message': 'Absence removed',
            'data': {
                'am': am,
                'date': date_str,
                'absences_list': existing,
                'absences_count': len(existing)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to remove absence'}), 500


# =============================================================================
# UNENROLLMENT API
# =============================================================================

@api_bp.route('/api/student/enrollment/<int:lab_id>', methods=['DELETE'])
@require_permission('registrations', 'cancel')
def api_unenroll_lab(lab_id):
    """Completely remove a student's enrollment from a lab and its group."""
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    lab_enrollment = RelLabStudent.query.filter_by(am=student_am, lab_id=lab_id).first()
    if not lab_enrollment:
        return jsonify({'success': False, 'message': 'No enrollment found for this lab'}), 404

    if lab_enrollment.status != '\u03a3\u03b5 \u0395\u03be\u03ad\u03bb\u03b9\u03be\u03b7':
        return jsonify({'success': False, 'message': 'Only active enrollments can be cancelled'}), 400

    academic_year = get_academic_year()

    try:
        group_enrollment = db.session.query(RelGroupStudent).join(
            LabGroup, RelGroupStudent.group_id == LabGroup.group_id
        ).join(
            RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
        ).filter(
            RelGroupStudent.am == student_am,
            RelLabGroup.lab_id == lab_id,
            LabGroup.year == academic_year
        ).first()

        if group_enrollment:
            audit_log('group_enrollment_deleted',
                      old_value=f"Student {student_am} in group {group_enrollment.group_id}",
                      reason='Student unenrolled from lab')
            db.session.delete(group_enrollment)

        absence = StudentMissesPerGroup.query.filter_by(
            am=student_am,
            group_id=group_enrollment.group_id if group_enrollment else 0
        ).first()
        if absence:
            db.session.delete(absence)

        audit_log('lab_enrollment_deleted',
                  old_value=f"Student {student_am} in lab {lab_id}, status={lab_enrollment.status}",
                  reason='Student unenrolled from lab')
        db.session.delete(lab_enrollment)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Η απεγγραφή ολοκληρώθηκε επιτυχώς.'}), 200

    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f'Unenroll failed: {e}')
        return jsonify({'success': False, 'message': 'Σφάλμα κατά την απεγγραφή'}), 500


# =============================================================================
# STUDENT PROFILE & NOTIFICATIONS APIs
# =============================================================================

@api_bp.route('/api/student/profile', methods=['GET'])
@require_permission('students_list', 'view_own_profile')
def api_get_student_profile():
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    student = Student.query.get(student_am)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found'}), 404

    return jsonify({
        'success': True,
        'data': {
            'am': student.am,
            'name': student.name,
            'semester': student.semester,
            'email': student.email
        }
    })


@api_bp.route('/api/student/profile', methods=['PUT'])
@require_permission('students_list', 'edit')
def api_update_student_profile():
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    student = Student.query.get(student_am)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found'}), 404

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    semester = data.get('semester')

    if name and len(name) < 3:
        return jsonify({'success': False, 'message': 'Name too short'}), 400
    if email and '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email'}), 400
    if semester is not None:
        try:
            semester = int(semester)
            if semester < 1 or semester > 12:
                return jsonify({'success': False, 'message': 'Semester must be 1-12'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Semester must be a number'}), 400

    try:
        old_values = f"name={student.name}, email={student.email}, semester={student.semester}"
        if name:
            student.name = name
        if email:
            student.email = email
        if semester is not None:
            student.semester = semester
        db.session.commit()

        new_values = f"name={student.name}, email={student.email}, semester={student.semester}"
        audit_log('profile_updated', old_value=old_values, new_value=new_values,
                  reason="Student updated profile")

        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {'am': student.am, 'name': student.name,
                     'semester': student.semester, 'email': student.email}
        })
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Update failed'}), 500


@api_bp.route('/api/student/notifications')
@require_permission('absences', 'view_own')
def api_student_notifications():
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    notifications = get_student_notifications(student_am)
    return jsonify({'success': True, 'count': len(notifications), 'data': notifications})


# =============================================================================
# PROFESSOR / ADMIN MANAGEMENT APIs
# =============================================================================

@api_bp.route('/api/labs/<int:lab_id>/details')
@require_permission('dashboard', 'view')
def api_lab_details(lab_id):
    """Return lab details including course name and assigned professors."""
    lab = CourseLab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'message': 'Lab not found'}), 404

    # Course info
    course_rel = RelCourseLab.query.filter_by(lab_id=lab_id).first()
    course = Coursename.query.get(course_rel.course_id) if course_rel else None

    # Professors assigned to any group of this lab
    professors = db.session.query(Professor).join(
        RelGroupProf, Professor.prof_id == RelGroupProf.prof_id
    ).join(
        RelLabGroup, RelGroupProf.group_id == RelLabGroup.group_id
    ).filter(
        RelLabGroup.lab_id == lab_id
    ).distinct().all()

    # Convert reg_limit to ISO format for HTML5 date inputs
    reg_limit_iso = ''
    if lab.reg_limit:
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                reg_limit_iso = datetime.strptime(lab.reg_limit, fmt).strftime('%Y-%m-%d')
                break
            except ValueError:
                continue

    return jsonify({
        'success': True,
        'data': {
            'lab_id': lab.lab_id,
            'name': lab.name,
            'description': lab.description,
            'maxusers': lab.maxusers,
            'reg_limit': lab.reg_limit,
            'reg_limit_iso': reg_limit_iso,
            'max_misses': lab.max_misses,
            'course_id': course_rel.course_id if course_rel else None,
            'course_name': course.name if course else None,
            'professors': [{
                'prof_id': p.prof_id,
                'name': p.name,
                'email': p.email
            } for p in professors]
        }
    })


@api_bp.route('/api/admin/labs/<int:lab_id>', methods=['PUT'])
@require_permission('registrations', 'manage')
def api_admin_edit_lab(lab_id):
    """Admin-only: update lab properties and course assignment."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    lab = CourseLab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'message': 'Lab not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    old_values = (f"name={lab.name}, maxusers={lab.maxusers}, "
                  f"reg_limit={lab.reg_limit}, max_misses={lab.max_misses}")
    old_course_rel = RelCourseLab.query.filter_by(lab_id=lab_id).first()
    old_course_id = old_course_rel.course_id if old_course_rel else None

    name = data.get('name', '').strip()
    course_id = data.get('course_id')
    max_users = data.get('max_users')
    date_end = data.get('date_end', '').strip() if data.get('date_end') else ''
    max_misses = data.get('max_misses')

    if name:
        lab.name = name

    if max_users is not None:
        try:
            lab.maxusers = int(max_users)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'max_users must be a number'}), 400

    if date_end:
        # Accept YYYY-MM-DD from the HTML date input, store as dd/mm/yyyy
        try:
            parsed = datetime.strptime(date_end, '%Y-%m-%d')
            lab.reg_limit = parsed.strftime('%d/%m/%Y')
        except ValueError:
            lab.reg_limit = date_end  # store as-is if format unknown

    if max_misses is not None:
        try:
            lab.max_misses = int(max_misses)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'max_misses must be a number'}), 400

    if course_id is not None:
        try:
            course_id = int(course_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid course_id'}), 400

        if not Coursename.query.get(course_id):
            return jsonify({'success': False, 'message': 'Course not found'}), 404

        if old_course_rel:
            old_course_rel.course_id = course_id
        else:
            db.session.add(RelCourseLab(course_id=course_id, lab_id=lab_id))

    db.session.commit()

    new_values = (f"name={lab.name}, maxusers={lab.maxusers}, "
                  f"reg_limit={lab.reg_limit}, max_misses={lab.max_misses}")
    audit_log('lab_updated',
              old_value=f"{old_values}, course_id={old_course_id}",
              new_value=f"{new_values}, course_id={course_id or old_course_id}",
              reason=f"Admin edited lab {lab_id}")

    new_course_rel = RelCourseLab.query.filter_by(lab_id=lab_id).first()
    new_course = Coursename.query.get(new_course_rel.course_id) if new_course_rel else None

    return jsonify({
        'success': True,
        'message': 'Lab updated',
        'data': {
            'lab_id': lab.lab_id,
            'name': lab.name,
            'maxusers': lab.maxusers,
            'reg_limit': lab.reg_limit,
            'max_misses': lab.max_misses,
            'course_id': new_course_rel.course_id if new_course_rel else None,
            'course_name': new_course.name if new_course else None
        }
    })


@api_bp.route('/api/admin/labs', methods=['POST'])
@require_permission('registrations', 'manage')
def api_admin_create_lab():
    """Admin-only: create a new lab and link it to a course."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    name = data.get('name', '').strip()
    course_id = data.get('course_id')
    max_users = data.get('max_users')
    date_end = data.get('date_end', '').strip() if data.get('date_end') else ''
    max_misses = data.get('max_misses')
    description = data.get('description', '').strip()

    if not name:
        return jsonify({'success': False, 'message': 'Lab name is required'}), 400

    try:
        max_users_int = int(max_users) if max_users is not None else 30
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'max_users must be a number'}), 400

    try:
        max_misses_int = int(max_misses) if max_misses is not None else 3
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'max_misses must be a number'}), 400

    reg_limit = ''
    if date_end:
        try:
            parsed = datetime.strptime(date_end, '%Y-%m-%d')
            reg_limit = parsed.strftime('%d/%m/%Y')
        except ValueError:
            reg_limit = date_end

    new_lab = CourseLab(
        name=name,
        description=description or '',
        maxusers=max_users_int,
        reg_limit=reg_limit,
        max_misses=max_misses_int
    )
    db.session.add(new_lab)
    db.session.flush()  # get the new lab_id

    if course_id is not None:
        try:
            course_id = int(course_id)
        except (ValueError, TypeError):
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Invalid course_id'}), 400
        if not Coursename.query.get(course_id):
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Course not found'}), 404
        db.session.add(RelCourseLab(course_id=course_id, lab_id=new_lab.lab_id))

    db.session.commit()

    audit_log('lab_created',
              new_value=f"lab_id={new_lab.lab_id}, name={name}, course_id={course_id}",
              reason='Admin created new lab')

    return jsonify({
        'success': True,
        'message': 'Lab created',
        'data': {
            'lab_id': new_lab.lab_id,
            'name': new_lab.name
        }
    }), 201


# =============================================================================
# ADMIN GROUP MANAGEMENT APIs
# =============================================================================

@api_bp.route('/api/admin/groups/<int:group_id>')
@require_permission('registrations', 'manage')
def api_admin_get_group(group_id):
    """Return group details including assigned professor for pre-filling edit form."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    group = LabGroup.query.get(group_id)
    if not group:
        return jsonify({'success': False, 'message': 'Group not found'}), 404

    lab_rel = RelLabGroup.query.filter_by(group_id=group_id).first()
    lab_id = lab_rel.lab_id if lab_rel else None
    lab = CourseLab.query.get(lab_id) if lab_id else None

    prof_rel = RelGroupProf.query.filter_by(group_id=group_id).first()
    prof_id = prof_rel.prof_id if prof_rel else None

    return jsonify({
        'success': True,
        'data': {
            'group_id': group.group_id,
            'daytime': group.daytime,
            'year': group.year,
            'finalize': group.finalize,
            'lab_id': lab_id,
            'lab_name': lab.name if lab else None,
            'prof_id': prof_id
        }
    })


@api_bp.route('/api/admin/groups', methods=['POST'])
@require_permission('registrations', 'manage')
def api_admin_create_group():
    """Admin-only: create a new group, link it to a lab, optionally assign a professor."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    lab_id = data.get('lab_id')
    day = data.get('day', '').strip()
    time_str = data.get('time', '').strip()
    prof_id = data.get('prof_id')

    if not lab_id:
        return jsonify({'success': False, 'message': 'Lab is required'}), 400
    if not day:
        return jsonify({'success': False, 'message': 'Day is required'}), 400
    if not time_str:
        return jsonify({'success': False, 'message': 'Time is required'}), 400

    lab = CourseLab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'message': 'Lab not found'}), 404

    daytime = day + ' ' + time_str
    academic_year = get_academic_year()

    new_group = LabGroup(
        daytime=daytime,
        year=academic_year,
        finalize=''
    )
    db.session.add(new_group)
    db.session.flush()

    db.session.add(RelLabGroup(lab_id=int(lab_id), group_id=new_group.group_id))

    if prof_id:
        prof = Professor.query.get(int(prof_id))
        if not prof:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Professor not found'}), 404
        db.session.add(RelGroupProf(prof_id=int(prof_id), group_id=new_group.group_id))

    db.session.commit()

    audit_log('group_created',
              new_value=f"group_id={new_group.group_id}, lab_id={lab_id}, daytime={daytime}, prof_id={prof_id}",
              reason='Admin created new group')

    return jsonify({
        'success': True,
        'message': 'Group created',
        'data': {
            'group_id': new_group.group_id,
            'daytime': new_group.daytime,
            'year': new_group.year
        }
    }), 201


@api_bp.route('/api/admin/groups/<int:group_id>', methods=['PUT'])
@require_permission('registrations', 'manage')
def api_admin_edit_group(group_id):
    """Admin-only: update group daytime and professor assignment."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    group = LabGroup.query.get(group_id)
    if not group:
        return jsonify({'success': False, 'message': 'Group not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    day = data.get('day', '').strip()
    time_str = data.get('time', '').strip()
    prof_id = data.get('prof_id')

    old_daytime = group.daytime

    if day and time_str:
        group.daytime = day + ' ' + time_str
    elif day:
        group.daytime = day
    elif time_str:
        group.daytime = time_str

    # Update professor assignment
    if prof_id is not None:
        # Remove all existing professor links for this group
        RelGroupProf.query.filter_by(group_id=group_id).delete()

        if prof_id:
            prof = Professor.query.get(int(prof_id))
            if not prof:
                db.session.rollback()
                return jsonify({'success': False, 'message': 'Professor not found'}), 404
            db.session.add(RelGroupProf(prof_id=int(prof_id), group_id=group_id))

    db.session.commit()

    new_prof_rel = RelGroupProf.query.filter_by(group_id=group_id).first()

    audit_log('group_updated',
              old_value=f"daytime={old_daytime}",
              new_value=f"daytime={group.daytime}, prof_id={new_prof_rel.prof_id if new_prof_rel else None}",
              reason=f"Admin edited group {group_id}")

    return jsonify({
        'success': True,
        'message': 'Group updated',
        'data': {
            'group_id': group.group_id,
            'daytime': group.daytime,
            'prof_id': new_prof_rel.prof_id if new_prof_rel else None
        }
    })


@api_bp.route('/api/labs/<int:lab_id>/description', methods=['PUT'])
@require_permission('labs', 'edit')
def api_edit_lab_description(lab_id):
    """Edit a lab description. Professors can only edit labs assigned to them."""
    lab = CourseLab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'message': 'Lab not found'}), 404

    if session.get('role') == 'professor':
        prof_id = session.get('schGrAcPersonID')
        owns = db.session.query(RelGroupProf).join(
            RelLabGroup, RelGroupProf.group_id == RelLabGroup.group_id
        ).filter(
            RelGroupProf.prof_id == prof_id,
            RelLabGroup.lab_id == lab_id
        ).first()
        if not owns:
            return jsonify({'success': False, 'message': 'Not assigned to this lab'}), 403

    data = request.get_json()
    if not data or not data.get('description', '').strip():
        return jsonify({'success': False, 'message': 'Description is required'}), 400

    old_desc = lab.description
    lab.description = data['description'].strip()
    db.session.commit()

    audit_log('lab_description_updated',
              old_value=old_desc, new_value=lab.description,
              reason=f"Lab {lab_id} description edited")

    return jsonify({'success': True, 'message': 'Description updated',
                    'data': {'lab_id': lab.lab_id, 'description': lab.description}})


@api_bp.route('/api/professor/profile', methods=['PUT'])
@require_permission('professors_list', 'edit_own_profile')
def api_edit_professor_profile():
    """Professor edits own profile (office, tel). Admin can edit any via ?prof_id=."""
    prof_id = request.args.get('prof_id', type=int)

    if session.get('role') == 'admin' and prof_id:
        professor = Professor.query.get(prof_id)
    else:
        professor = Professor.query.get(session.get('schGrAcPersonID'))

    if not professor:
        return jsonify({'success': False, 'message': 'Professor not found'}), 404

    if session.get('role') == 'professor' and str(professor.prof_id) != session.get('schGrAcPersonID'):
        return jsonify({'success': False, 'message': 'Cannot edit another professor'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    old_values = f"office={professor.office}, tel={professor.tel}"

    office = data.get('office', '').strip()
    tel = data.get('tel', '').strip()
    if office:
        professor.office = office
    if tel:
        professor.tel = tel

    db.session.commit()

    audit_log('professor_profile_updated',
              old_value=old_values,
              new_value=f"office={professor.office}, tel={professor.tel}",
              reason="Professor profile edited")

    return jsonify({
        'success': True, 'message': 'Profile updated',
        'data': {'prof_id': professor.prof_id, 'name': professor.name,
                 'office': professor.office, 'tel': professor.tel}
    })


# =============================================================================
# ADMIN ELIGIBILITY APIs
# =============================================================================

@api_bp.route('/api/admin/course/<int:course_id>/import-eligible', methods=['POST'])
@require_permission('registrations', 'manage')
def api_import_eligible(course_id):
    """Upload a CSV of eligible student AMs for a course (admin only)."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    if not Coursename.query.get(course_id):
        return jsonify({'success': False, 'message': 'Course not found'}), 404

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'message': 'Empty filename'}), 400

    try:
        raw = file.read()
        # Try UTF-8-BOM first, fall back to UTF-8, then latin-1
        for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return jsonify({'success': False, 'message': 'Unable to decode file'}), 400

        # Robust parsing: split by newlines AND commas so we handle
        # both standard CSV rows and comma-separated AMs on a single line.
        tokens = []
        for line in text.splitlines():
            tokens.extend(line.split(','))
        ams = []
        for token in tokens:
            val = token.strip()
            if val.isdigit():
                ams.append(int(val))

        if not ams:
            return jsonify({'success': False, 'message': 'No valid AMs found in file'}), 400

        # Replace existing list
        CourseEligibility.query.filter_by(course_id=course_id).delete()
        for am in ams:
            db.session.add(CourseEligibility(course_id=course_id, am=am))
        db.session.commit()

        audit_log('eligibility_imported',
                  new_value=f'Course {course_id}: {len(ams)} students imported',
                  reason='Admin uploaded eligibility CSV')

        return jsonify({
            'success': True,
            'message': f'{len(ams)} eligible students imported',
            'data': {'course_id': course_id, 'count': len(ams)}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Import failed'}), 500


@api_bp.route('/api/admin/course/<int:course_id>/eligible')
@require_permission('registrations', 'manage')
def api_get_eligible(course_id):
    """Get the count of eligible students for a course."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403
    count = CourseEligibility.query.filter_by(course_id=course_id).count()
    return jsonify({'success': True, 'data': {'course_id': course_id, 'count': count}})


@api_bp.route('/api/admin/course/<int:course_id>/clear-eligible', methods=['DELETE'])
@require_permission('registrations', 'manage')
def api_clear_eligible(course_id):
    """Remove all eligibility records for a course (opens registration to everyone)."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403
    deleted = CourseEligibility.query.filter_by(course_id=course_id).delete()
    db.session.commit()
    audit_log('eligibility_cleared',
              old_value=f'Course {course_id}: {deleted} records removed',
              reason='Admin cleared eligibility list')
    return jsonify({'success': True, 'message': f'{deleted} records cleared'})


# =============================================================================
# CSV EXPORT APIs
# =============================================================================

def _make_csv_response(rows, headers, filename):
    """Build a UTF-8 BOM CSV Response from a list of row-dicts."""
    buf = io.StringIO()
    buf.write('\ufeff')  # BOM for Excel
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    output = buf.getvalue()
    return Response(
        output,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@api_bp.route('/api/professor/group/<int:group_id>/export')
@require_permission('students_list', 'view_professor_students')
def api_export_group_csv(group_id):
    """Export group roster as CSV (professor who owns the group, or admin)."""
    err = _check_group_ownership(group_id)
    if err:
        return err

    lab_rel = RelLabGroup.query.filter_by(group_id=group_id).first()
    lab_id = lab_rel.lab_id if lab_rel else None

    students = db.session.query(Student).join(
        RelGroupStudent, Student.am == RelGroupStudent.am
    ).filter(RelGroupStudent.group_id == group_id).order_by(Student.name).all()

    rows = []
    for s in students:
        absence_rec = StudentMissesPerGroup.query.filter_by(
            am=s.am, group_id=group_id
        ).first()
        dates_str = absence_rec.misses if absence_rec else ''
        dates_list = [d.strip() for d in dates_str.split(',') if d.strip()] if dates_str else []

        grade = 0
        status = STATUS_IN_PROGRESS
        if lab_id:
            enroll = RelLabStudent.query.filter_by(am=s.am, lab_id=lab_id).first()
            if enroll:
                grade = enroll.grade
                status = enroll.status

        rows.append({
            '\u0391.\u039c.': s.am,
            '\u039f\u03bd\u03bf\u03bc\u03b1\u03c4\u03b5\u03c0\u03ce\u03bd\u03c5\u03bc\u03bf': s.name,
            'Email': s.email,
            '\u0395\u03be\u03ac\u03bc\u03b7\u03bd\u03bf': s.semester,
            '\u0392\u03b1\u03b8\u03bc\u03cc\u03c2': grade,
            '\u039a\u03b1\u03c4\u03ac\u03c3\u03c4\u03b1\u03c3\u03b7': status,
            '\u03a3\u03cd\u03bd\u03bf\u03bb\u03bf \u0391\u03c0\u03bf\u03c5\u03c3\u03b9\u03ce\u03bd': len(dates_list),
            '\u0397\u03bc\u03b5\u03c1\u03bf\u03bc\u03b7\u03bd\u03af\u03b5\u03c2 \u0391\u03c0\u03bf\u03c5\u03c3\u03b9\u03ce\u03bd': ', '.join(dates_list)
        })

    headers = [
        '\u0391.\u039c.', '\u039f\u03bd\u03bf\u03bc\u03b1\u03c4\u03b5\u03c0\u03ce\u03bd\u03c5\u03bc\u03bf',
        'Email', '\u0395\u03be\u03ac\u03bc\u03b7\u03bd\u03bf',
        '\u0392\u03b1\u03b8\u03bc\u03cc\u03c2', '\u039a\u03b1\u03c4\u03ac\u03c3\u03c4\u03b1\u03c3\u03b7',
        '\u03a3\u03cd\u03bd\u03bf\u03bb\u03bf \u0391\u03c0\u03bf\u03c5\u03c3\u03b9\u03ce\u03bd',
        '\u0397\u03bc\u03b5\u03c1\u03bf\u03bc\u03b7\u03bd\u03af\u03b5\u03c2 \u0391\u03c0\u03bf\u03c5\u03c3\u03b9\u03ce\u03bd'
    ]

    audit_log('csv_export', new_value=f'Group {group_id} roster exported ({len(rows)} students)')
    return _make_csv_response(rows, headers, f'group_roster_{group_id}.csv')


@api_bp.route('/api/admin/lab/<int:lab_id>/export')
@require_permission('registrations', 'manage')
def api_export_lab_csv(lab_id):
    """Export full lab roster across all groups as CSV (admin only)."""
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403

    lab = CourseLab.query.get(lab_id)
    if not lab:
        return jsonify({'success': False, 'message': 'Lab not found'}), 404

    academic_year = get_academic_year()

    # All groups belonging to this lab in the current year
    groups = db.session.query(LabGroup).join(
        RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
    ).filter(
        RelLabGroup.lab_id == lab_id,
        LabGroup.year == academic_year
    ).all()
    group_map = {g.group_id: g.daytime for g in groups}
    group_ids = list(group_map.keys())

    if not group_ids:
        return jsonify({'success': False, 'message': 'No groups for this lab in current year'}), 404

    # Students enrolled in any of these groups
    enrolled = db.session.query(Student, RelGroupStudent.group_id).join(
        RelGroupStudent, Student.am == RelGroupStudent.am
    ).filter(RelGroupStudent.group_id.in_(group_ids)).order_by(Student.name).all()

    rows = []
    for student, gid in enrolled:
        enroll = RelLabStudent.query.filter_by(am=student.am, lab_id=lab_id).first()
        grade = enroll.grade if enroll else 0
        status = enroll.status if enroll else STATUS_IN_PROGRESS

        absence_rec = StudentMissesPerGroup.query.filter_by(am=student.am, group_id=gid).first()
        abs_count = len([d.strip() for d in absence_rec.misses.split(',') if d.strip()]) if absence_rec else 0

        rows.append({
            '\u0391.\u039c.': student.am,
            '\u039f\u03bd\u03bf\u03bc\u03b1\u03c4\u03b5\u03c0\u03ce\u03bd\u03c5\u03bc\u03bf': student.name,
            '\u03a4\u03bc\u03ae\u03bc\u03b1': group_map.get(gid, ''),
            '\u0392\u03b1\u03b8\u03bc\u03cc\u03c2': grade,
            '\u039a\u03b1\u03c4\u03ac\u03c3\u03c4\u03b1\u03c3\u03b7': status,
            '\u03a3\u03cd\u03bd\u03bf\u03bb\u03bf \u0391\u03c0\u03bf\u03c5\u03c3\u03b9\u03ce\u03bd': abs_count
        })

    headers = [
        '\u0391.\u039c.', '\u039f\u03bd\u03bf\u03bc\u03b1\u03c4\u03b5\u03c0\u03ce\u03bd\u03c5\u03bc\u03bf',
        '\u03a4\u03bc\u03ae\u03bc\u03b1',
        '\u0392\u03b1\u03b8\u03bc\u03cc\u03c2', '\u039a\u03b1\u03c4\u03ac\u03c3\u03c4\u03b1\u03c3\u03b7',
        '\u03a3\u03cd\u03bd\u03bf\u03bb\u03bf \u0391\u03c0\u03bf\u03c5\u03c3\u03b9\u03ce\u03bd'
    ]

    audit_log('csv_export', new_value=f'Lab {lab_id} full roster exported ({len(rows)} students)')
    return _make_csv_response(rows, headers, f'lab_{lab_id}_full_roster.csv')


# =============================================================================
# LEGACY JSON ENDPOINTS (Groups, Absences, Profile, Professors)
# =============================================================================

@api_bp.route('/groups')
@require_permission('groups', 'view')
def list_groups():
    groups = LabGroup.query.all()
    groups_data = []
    for group in groups:
        group_dict = {
            'group_id': group.group_id,
            'daytime': group.daytime,
            'year': group.year,
            'finalize': group.finalize
        }
        groups_data.append(mask_pii(group_dict))
    return jsonify(groups_data)


@api_bp.route('/groups/<int:group_id>/join', methods=['POST'])
@require_permission('groups', 'join')
def join_group(group_id):
    student_am = session['schGrAcPersonID']
    success, message = transactional_enrollment(student_am, group_id)
    status_code = 200 if success else 400
    return jsonify({'success': success, 'message': message}), status_code


@api_bp.route('/groups/<int:group_id>/leave', methods=['POST'])
@require_permission('groups', 'leave')
def leave_group(group_id):
    student_am = session['schGrAcPersonID']
    try:
        enrollment = RelGroupStudent.query.filter_by(am=student_am, group_id=group_id).first()
        if not enrollment:
            return jsonify({'success': False, 'message': 'Not enrolled in this group'}), 400

        audit_log('enrollment_deleted',
                  old_value=f"Student {student_am} was enrolled in group {group_id}",
                  reason='Student left group')
        db.session.delete(enrollment)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Successfully left group'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to leave group'}), 500


@api_bp.route('/groups/<int:group_id>/absences', methods=['GET'])
@require_permission('absences', 'view_group')
def view_group_absences(group_id):
    absences = StudentMissesPerGroup.query.filter_by(group_id=group_id).all()
    absences_data = []
    for absence in absences:
        student = Student.query.get(absence.am)
        absences_data.append({
            'student_am': mask_pii({'am': absence.am})['am'],
            'student_name': student.name if student else 'Unknown',
            'date': absence.misses
        })
    return jsonify(absences_data)


@api_bp.route('/groups/<int:group_id>/absences', methods=['POST'])
@require_permission('absences', 'edit_group_absences')
def record_group_absence(group_id):
    data = request.get_json()
    student_am = data.get('student_am')
    date = data.get('date')
    reason = data.get('reason')

    if not student_am or not date:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    success, message = record_absence(student_am, group_id, date, reason)
    status_code = 200 if success else 400
    return jsonify({'success': success, 'message': message}), status_code


@api_bp.route('/students/profile')
@require_permission('students_list', 'view_own_profile')
def view_own_profile():
    student_am = session['schGrAcPersonID']
    student = Student.query.get(student_am)
    if not student:
        return jsonify({'error': 'Student not found'}), 404

    profile = mask_pii({
        'am': student.am, 'name': student.name,
        'semester': student.semester, 'email': student.email
    })
    return jsonify(profile)


@api_bp.route('/professors')
@require_permission('professors_list', 'view')
def list_professors():
    professors = Professor.query.all()
    professors_data = []
    for prof in professors:
        prof_dict = {
            'prof_id': prof.prof_id, 'name': prof.name,
            'status': prof.status, 'office': prof.office,
            'email': prof.email, 'tel': prof.tel
        }
        professors_data.append(mask_pii(prof_dict))
    return jsonify(professors_data)
