import json
import functools
import os
from flask import session, abort, request, current_app
from flask_login import current_user
from app.models import db, Student, Professor, RelGroupStudent, LabGroup, CourseLab
from sqlalchemy import and_
import logging

# Configure logging for audit
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PermissionMatrix:
    def __init__(self):
        # Use test matrix if it exists (for testing), otherwise use production matrix
        matrix_file = 'test_permission_matrix.json' if os.path.exists('test_permission_matrix.json') else 'app/templates/permission_matrix.json'
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
        
        # Check if user is professor
        prof = Professor.query.filter_by(prof_id=user_id).first()
        if prof:
            return 'professor'
        
        # Check if user is student
        student = Student.query.filter_by(am=user_id).first()
        if student:
            return 'student'
        
        return 'guest'

def require_permission(resource, action):
    """Decorator for requiring specific permission"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'schGrAcPersonID' not in session:
                abort(401, description="Authentication required")
            
            user_id = session['schGrAcPersonID']
            matrix = PermissionMatrix()
            role = matrix.get_user_role(user_id)
            
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

def audit_log(action, old_value=None, new_value=None, reason=None):
    """Log audit trail for critical actions"""
    user_id = session.get('schGrAcPersonID', 'unknown')
    user_role = session.get('role', 'unknown')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'user_role': user_role,
        'action': action,
        'ip_address': request.remote_addr,
        'old_value': old_value,
        'new_value': new_value,
        'reason': reason
    }
    
    logger.info(f"AUDIT: {json.dumps(log_entry)}")

def mask_pii(data, fields_to_mask=['email', 'am', 'tel']):
    """Mask PII fields in public views"""
    if isinstance(data, dict):
        masked = data.copy()
        for field in fields_to_mask:
            if field in masked and masked[field]:
                if field == 'email':
                    parts = masked[field].split('@')
                    if len(parts) == 2:
                        masked[field] = f"{parts[0][:2]}***@{parts[1]}"
                elif field in ['am', 'tel']:
                    masked[field] = f"{str(masked[field])[:2]}***{str(masked[field])[-2:]}"
        return masked
    return data

def check_enrollment_preconditions(student_am, group_id):
    """Check if student can join group (enrolled in course & capacity available)"""
    try:
        # Get group and related lab/course info
        group = LabGroup.query.get(group_id)
        if not group:
            return False, "Group not found"
        
        # Check if student is enrolled in the course related to this group
        # This requires joining multiple tables - simplified for now
        lab_groups = db.session.query(RelLabGroup).filter_by(group_id=group_id).all()
        if not lab_groups:
            return False, "No labs associated with group"
        
        # Check current enrollment count
        current_enrollments = RelGroupStudent.query.filter_by(group_id=group_id).count()
        
        # Get max capacity from related lab
        lab = CourseLab.query.join(RelLabGroup).filter(RelLabGroup.group_id == group_id).first()
        if not lab:
            return False, "Lab not found"
        
        if current_enrollments >= lab.maxusers:
            return False, "Group is full"
        
        return True, "Eligible to join"
        
    except Exception as e:
        logger.error(f"Error checking enrollment preconditions: {e}")
        return False, "System error"

def transactional_enrollment(student_am, group_id):
    """Enroll student in group with transactional safety"""
    try:
        # Start transaction
        db.session.begin()
        
        # Check preconditions again within transaction
        can_join, message = check_enrollment_preconditions(student_am, group_id)
        if not can_join:
            db.session.rollback()
            return False, message
        
        # Check if already enrolled
        existing = RelGroupStudent.query.filter_by(
            am=student_am, group_id=group_id
        ).first()
        
        if existing:
            db.session.rollback()
            return False, "Already enrolled"
        
        # Create enrollment with audit
        enrollment = RelGroupStudent(
            am=student_am,
            group_id=group_id,
            group_reg_daymonth=f"{datetime.now().day}/{datetime.now().month}",
            group_reg_year=datetime.now().year
        )
        
        db.session.add(enrollment)
        db.session.commit()
        
        # Audit log
        audit_log(
            action="enrollment_created",
            new_value=f"Student {student_am} enrolled in group {group_id}",
            reason="Student initiated enrollment"
        )
        
        return True, "Enrollment successful"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Transaction failed: {e}")
        return False, "Enrollment failed"

def record_absence(student_am, group_id, date, reason=None):
    """Record student absence with audit trail"""
    try:
        # Check if professor/admin is recording
        user_role = session.get('role')
        if user_role not in ['professor', 'admin']:
            return False, "Insufficient permissions to record absence"
        
        # Record absence
        absence = StudentMissesPerGroup(
            am=student_am,
            group_id=group_id,
            misses=date
        )
        
        db.session.add(absence)
        db.session.commit()
        
        # Audit log
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

# Import datetime for audit logs
from datetime import datetime
