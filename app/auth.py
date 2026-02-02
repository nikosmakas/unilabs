import json
import functools
import os
from flask import session, abort, request
from models import db, Student, Professor, RelGroupStudent, LabGroup, CourseLab, RelLabStudent, RelLabGroup, StudentMissesPerGroup
from sqlalchemy import and_
import logging
from datetime import datetime

# Configure logging for audit
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# STATUS VALUES (Greek)
# =============================================================================
STATUS_IN_PROGRESS = "Σε Εξέλιξη"
STATUS_FAILED = "Αποτυχία"
STATUS_COMPLETED = "Ολοκληρωμένο"

# =============================================================================
# PERMISSION MATRIX
# =============================================================================

class PermissionMatrix:
    def __init__(self):
        matrix_file = 'test_permission_matrix.json' if os.path.exists('test_permission_matrix.json') else 'templates/permission_matrix.json'
        with open(matrix_file, 'r', encoding='utf-8') as f:
            self.matrix = json.load(f)
    
    def has_permission(self, role, resource, action):
        """Check if role has permission for resource.action"""
        if role not in self.matrix['roles']:
            return False
        
        if resource not in self.matrix['resources']:
            return False
        
        resource_config = self.matrix['resources'][resource]
        if action not in resource_config:
            return False
        
        return role in resource_config[action]
    
    def get_user_role(self, user_id):
        """Get user role from session or database"""
        if 'role' in session:
            return session['role']
        
        prof = Professor.query.filter_by(prof_id=user_id).first()
        if prof:
            return 'professor'
        
        student = Student.query.filter_by(am=user_id).first()
        if student:
            return 'student'
        
        return 'guest'

# =============================================================================
# DECORATORS
# =============================================================================

def require_permission(resource, action):
    """Decorator for requiring specific permission"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            matrix = PermissionMatrix()
            if 'schGrAcPersonID' in session:
                user_id = session['schGrAcPersonID']
                role = matrix.get_user_role(user_id)
            else:
                role = 'guest'
            
            if not matrix.has_permission(role, resource, action):
                logger.warning(f"Permission denied: {role} tried to access {resource}.{action}")
                abort(403, description="Insufficient permissions")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role(*roles):
    """Decorator for requiring specific role(s)"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'schGrAcPersonID' not in session:
                abort(401, description="Authentication required")
            
            user_role = session.get('role', 'guest')
            if user_role not in roles:
                logger.warning(f"Role denied: {user_role} tried to access endpoint requiring {roles}")
                abort(403, description="Insufficient role permissions")
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def audit_log(action, old_value=None, new_value=None, reason=None):
    """Log audit trail for critical actions"""
    user_id = session.get('schGrAcPersonID', 'unknown')
    user_role = session.get('role', 'unknown')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'user_role': user_role,
        'action': action,
        'ip_address': request.remote_addr if request else 'unknown',
        'old_value': old_value,
        'new_value': new_value,
        'reason': reason
    }
    
    logger.info(f"AUDIT: {json.dumps(log_entry, ensure_ascii=False)}")

def mask_pii(data, fields_to_mask=['email', 'am', 'tel']):
    """Mask PII fields in public views"""
    if isinstance(data, dict):
        masked = data.copy()
        for field in fields_to_mask:
            if field in masked and masked[field]:
                if field == 'email':
                    parts = str(masked[field]).split('@')
                    if len(parts) == 2:
                        masked[field] = f"{parts[0][:2]}***@{parts[1]}"
                elif field in ['am', 'tel']:
                    val = str(masked[field])
                    masked[field] = f"{val[:2]}***{val[-2:]}" if len(val) > 4 else "***"
        return masked
    return data

def get_academic_year():
    """
    Υπολογισμός ακαδημαϊκού έτους.
    Αν day_of_year < 35, χρησιμοποίησε το προηγούμενο έτος.
    """
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday
    current_year = today.year
    
    if day_of_year < 35:
        return current_year - 1
    return current_year

# =============================================================================
# REGISTRATION VALIDATION FUNCTIONS
# =============================================================================

def validate_registration_period(lab_id):
    """
    Έλεγχος αν η εγγραφή είναι εντός της επιτρεπόμενης περιόδου.
    
    Returns: (bool, str) - (is_valid, message)
    """
    lab = CourseLab.query.get(lab_id)
    if not lab:
        return False, "Το εργαστήριο δεν βρέθηκε"
    
    if not lab.reg_limit:
        return True, "Δεν υπάρχει όριο εγγραφών"
    
    try:
        reg_limit_date = datetime.strptime(lab.reg_limit, "%d/%m/%Y").date()
        today = datetime.now().date()
        
        if today > reg_limit_date:
            return False, "Δεν επιτρέπεται η αλλαγή / εγγραφή σε τμήμα."
        
        return True, f"Εγγραφές έως {lab.reg_limit}"
    except ValueError:
        try:
            reg_limit_date = datetime.strptime(lab.reg_limit, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            if today > reg_limit_date:
                return False, "Δεν επιτρέπεται η αλλαγή / εγγραφή σε τμήμα."
            
            return True, f"Εγγραφές έως {lab.reg_limit}"
        except ValueError:
            logger.warning(f"Could not parse reg_limit: {lab.reg_limit}")
            return True, "Μη έγκυρη ημερομηνία ορίου"

def check_group_capacity(group_id, lab_id):
    """
    Έλεγχος χωρητικότητας τμήματος.
    
    Returns: (bool, str, dict) - (has_space, message, occupancy_info)
    """
    current_count = RelGroupStudent.query.filter_by(group_id=group_id).count()
    
    lab = CourseLab.query.get(lab_id)
    if not lab:
        return False, "Το εργαστήριο δεν βρέθηκε", {}
    
    max_users = lab.maxusers
    available = max_users - current_count
    
    occupancy = {
        'current': current_count,
        'max': max_users,
        'available': max(0, available),
        'percentage': round((current_count / max_users * 100), 1) if max_users > 0 else 0
    }
    
    if current_count >= max_users:
        return False, "Το τμήμα δεν έχει ανοιχτές θέσεις", occupancy
    
    return True, f"Διαθέσιμες θέσεις: {available}", occupancy

def get_student_lab_status(student_am, lab_id):
    """
    Λήψη κατάστασης φοιτητή σε εργαστήριο.
    
    Returns: dict with status, failures, or None if not enrolled
    """
    enrollment = RelLabStudent.query.filter_by(am=student_am, lab_id=lab_id).first()
    
    if not enrollment:
        return None
    
    return {
        'status': enrollment.status,
        'failures': getattr(enrollment, 'failures', 0),
        'reg_month': enrollment.reg_month,
        'reg_year': enrollment.reg_year
    }

def check_existing_enrollment(student_am, lab_id, group_id, academic_year):
    """
    Έλεγχος υπάρχουσας εγγραφής φοιτητή.
    
    Returns: (enrollment_type, message)
    """
    lab_enrollment = RelLabStudent.query.filter_by(am=student_am, lab_id=lab_id).first()
    
    if not lab_enrollment:
        return 'none', "Νέα εγγραφή"
    
    if lab_enrollment.status == STATUS_FAILED:
        return 'failed', "Επανεγγραφή μετά από αποτυχία"
    
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
        if group_enrollment.group_id == group_id:
            return 'same_group', "Είστε ήδη εγγεγραμμένος σε αυτό το τμήμα"
        else:
            return 'different_group', "Είστε εγγεγραμμένος σε άλλο τμήμα αυτού του εργαστηρίου"
    
    return 'none', "Νέα εγγραφή σε τμήμα"

# =============================================================================
# MAIN REGISTRATION FUNCTIONS
# =============================================================================

def register_student_to_lab(student_am, lab_id, group_id):
    """
    Πλήρης εγγραφή φοιτητή σε εργαστήριο και τμήμα.
    
    Returns: (bool, str, dict) - (success, message, details)
    """
    academic_year = get_academic_year()
    
    period_valid, period_msg = validate_registration_period(lab_id)
    if not period_valid:
        return False, period_msg, {'error_type': 'registration_closed'}
    
    has_space, capacity_msg, occupancy = check_group_capacity(group_id, lab_id)
    if not has_space:
        return False, capacity_msg, {'error_type': 'group_full', 'occupancy': occupancy}
    
    enrollment_type, enrollment_msg = check_existing_enrollment(
        student_am, lab_id, group_id, academic_year
    )
    
    try:
        if enrollment_type == 'same_group':
            return False, enrollment_msg, {'error_type': 'already_enrolled'}
        
        if enrollment_type == 'different_group':
            return False, "Χρησιμοποιήστε την αλλαγή τμήματος", {'error_type': 'use_change_group'}
        
        if enrollment_type == 'failed':
            lab_enrollment = RelLabStudent.query.filter_by(am=student_am, lab_id=lab_id).first()
            old_failures = lab_enrollment.misses if hasattr(lab_enrollment, 'misses') else 0
            
            lab_enrollment.status = STATUS_IN_PROGRESS
            lab_enrollment.misses = old_failures + 1
            lab_enrollment.reg_month = datetime.now().month
            lab_enrollment.reg_year = datetime.now().year
            
            audit_log(
                'lab_reregistration',
                old_value=f"Status: {STATUS_FAILED}, Failures: {old_failures}",
                new_value=f"Status: {STATUS_IN_PROGRESS}, Failures: {old_failures + 1}",
                reason="Student re-registered after failure"
            )
        else:
            new_lab_enrollment = RelLabStudent(
                am=student_am,
                lab_id=lab_id,
                misses=0,
                grade=0,
                reg_month=datetime.now().month,
                reg_year=datetime.now().year,
                status=STATUS_IN_PROGRESS
            )
            db.session.add(new_lab_enrollment)
            
            audit_log(
                'lab_registration_created',
                new_value=f"Student {student_am} registered to lab {lab_id}",
                reason="New lab registration"
            )
        
        new_group_enrollment = RelGroupStudent(
            am=student_am,
            group_id=group_id,
            group_reg_daymonth=f"{datetime.now().day}/{datetime.now().month}",
            group_reg_year=datetime.now().year
        )
        db.session.add(new_group_enrollment)
        
        db.session.commit()
        
        audit_log(
            'group_enrollment_created',
            new_value=f"Student {student_am} enrolled in group {group_id}",
            reason="Registration completed"
        )
        
        return True, "Η εγγραφή ολοκληρώθηκε επιτυχώς!", {
            'enrollment_type': enrollment_type,
            'group_id': group_id,
            'lab_id': lab_id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration failed: {e}")
        return False, "Σφάλμα στην επικοινωνία. Προσπαθήστε αργότερα", {'error_type': 'system_error'}

def change_student_group(student_am, old_group_id, new_group_id, lab_id):
    """
    Αλλαγή τμήματος φοιτητή.
    
    Returns: (bool, str, dict) - (success, message, details)
    """
    period_valid, period_msg = validate_registration_period(lab_id)
    if not period_valid:
        return False, period_msg, {'error_type': 'registration_closed'}
    
    has_space, capacity_msg, occupancy = check_group_capacity(new_group_id, lab_id)
    if not has_space:
        return False, capacity_msg, {'error_type': 'group_full', 'occupancy': occupancy}
    
    existing_enrollment = RelGroupStudent.query.filter_by(
        am=student_am, group_id=old_group_id
    ).first()
    
    if not existing_enrollment:
        return False, "Δεν είστε εγγεγραμμένος στο τρέχον τμήμα", {'error_type': 'not_enrolled'}
    
    logger.info(f"Changing group for student {student_am} from {old_group_id} to {new_group_id}")
    
    try:
        existing_enrollment.group_id = new_group_id
        existing_enrollment.group_reg_daymonth = f"{datetime.now().day}/{datetime.now().month}"
        existing_enrollment.group_reg_year = datetime.now().year
        
        db.session.commit()
        
        audit_log(
            'group_changed',
            old_value=f"Group {old_group_id}",
            new_value=f"Group {new_group_id}",
            reason="Student changed group"
        )
        
        return True, "Η αλλαγή τμήματος ολοκληρώθηκε επιτυχώς!", {
            'old_group_id': old_group_id,
            'new_group_id': new_group_id
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Group change failed: {e}")
        return False, "Σφάλμα στην επικοινωνία. Προσπαθήστε αργότερα", {'error_type': 'system_error'}

def get_student_enrollments(student_am, academic_year=None):
    """
    Λήψη εγγραφών φοιτητή.
    
    Returns: List of enrollment dictionaries
    """
    if academic_year is None:
        academic_year = get_academic_year()
    
    enrollments = db.session.query(
        CourseLab.name.label('lab_name'),
        CourseLab.lab_id,
        LabGroup.daytime,
        LabGroup.group_id,
        RelLabStudent.status,
        RelLabStudent.misses,
        RelLabStudent.grade
    ).join(
        RelLabStudent, CourseLab.lab_id == RelLabStudent.lab_id
    ).join(
        RelLabGroup, CourseLab.lab_id == RelLabGroup.lab_id
    ).join(
        LabGroup, RelLabGroup.group_id == LabGroup.group_id
    ).join(
        RelGroupStudent, and_(
            LabGroup.group_id == RelGroupStudent.group_id,
            RelLabStudent.am == RelGroupStudent.am
        )
    ).filter(
        RelLabStudent.am == student_am,
        LabGroup.year == academic_year
    ).distinct().all()
    
    result = []
    for e in enrollments:
        absences = StudentMissesPerGroup.query.filter_by(
            am=student_am, group_id=e.group_id
        ).first()
        
        result.append({
            'lab_name': e.lab_name,
            'lab_id': e.lab_id,
            'group_daytime': e.daytime,
            'group_id': e.group_id,
            'status': e.status,
            'absences': absences.misses if absences else '-',
            'grade': e.grade
        })
    
    return result

# =============================================================================
# LEGACY FUNCTIONS (for backwards compatibility)
# =============================================================================

def check_enrollment_preconditions(student_am, group_id):
    """Check if student can join group"""
    try:
        group = LabGroup.query.get(group_id)
        if not group:
            return False, "Group not found"
        
        lab_group_rel = RelLabGroup.query.filter_by(group_id=group_id).first()
        if not lab_group_rel:
            return False, "No labs associated with group"
        
        lab_id = lab_group_rel.lab_id
        
        has_space, msg, _ = check_group_capacity(group_id, lab_id)
        if not has_space:
            return False, msg
        
        return True, "Eligible to join"
        
    except Exception as e:
        logger.error(f"Error checking enrollment preconditions: {e}")
        return False, "System error"

def transactional_enrollment(student_am, group_id):
    """Enroll student in group with transactional safety"""
    try:
        lab_group_rel = RelLabGroup.query.filter_by(group_id=group_id).first()
        if not lab_group_rel:
            return False, "No lab associated with this group"
        
        lab_id = lab_group_rel.lab_id
        
        success, message, details = register_student_to_lab(student_am, lab_id, group_id)
        return success, message
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Transaction failed: {e}")
        return False, "Enrollment failed"

def record_absence(student_am, group_id, date, reason=None):
    """Record student absence with audit trail"""
    try:
        user_role = session.get('role')
        if user_role not in ['professor', 'admin']:
            return False, "Insufficient permissions to record absence"
        
        existing = StudentMissesPerGroup.query.filter_by(
            am=student_am, group_id=group_id
        ).first()
        
        if existing:
            if existing.misses:
                existing.misses = f"{existing.misses}, {date}"
            else:
                existing.misses = date
        else:
            absence = StudentMissesPerGroup(
                am=student_am,
                group_id=group_id,
                misses=date
            )
            db.session.add(absence)
        
        db.session.commit()
        
        audit_log(
            action="absence_recorded",
            new_value=f"Absence recorded for student {student_am} in group {group_id} on {date}",
            reason=reason or "Professor recorded absence"
        )
        
        return True, "Absence recorded"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error recording absence: {e}")
        return False, "Failed to record absence"
