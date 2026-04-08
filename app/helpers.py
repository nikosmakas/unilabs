from models import (
    Student, CourseLab, RelGroupStudent, db
)
from auth import audit_log, get_academic_year, get_student_enrollments


def get_group_occupancy(group_id, lab_id):
    """Calculate group occupancy stats."""
    current_count = RelGroupStudent.query.filter_by(group_id=group_id).count()
    lab = CourseLab.query.get(lab_id)
    max_users = lab.maxusers if lab else 0

    return {
        'current': current_count,
        'max': max_users,
        'available': max(0, max_users - current_count),
        'percentage': round((current_count / max_users * 100), 1) if max_users > 0 else 0,
        'is_full': current_count >= max_users
    }


def get_student_notifications(student_am):
    """Fetch absence-based notifications for a student."""
    academic_year = get_academic_year()
    notifications = []

    enrollments = get_student_enrollments(student_am, academic_year)

    for e in enrollments:
        if e['absences'] and e['absences'] != '-':
            absence_count = len(e['absences'].split(',')) if isinstance(e['absences'], str) else 0
            lab = CourseLab.query.get(e['lab_id'])
            max_misses = lab.max_misses if lab else 3

            if absence_count > 0:
                notifications.append({
                    'type': 'warning' if absence_count >= max_misses - 1 else 'info',
                    'lab_name': e['lab_name'],
                    'message': f"You have {absence_count} absences in {e['lab_name']}",
                    'absences': absence_count,
                    'max_absences': max_misses,
                    'is_critical': absence_count >= max_misses
                })

    return notifications


def create_or_get_student(am, name, email=None):
    """Create a new student or return the existing one."""
    student = Student.query.filter_by(am=am).first()

    if student:
        return student, False

    new_student = Student(
        am=am,
        name=name,
        semester=1,
        pwd='',
        email=email or ''
    )

    try:
        db.session.add(new_student)
        db.session.commit()

        audit_log(
            'student_created',
            new_value=f"Student {am} ({name}) created via CAS",
            reason="First CAS login"
        )

        return new_student, True
    except Exception:
        db.session.rollback()
        return None, False
