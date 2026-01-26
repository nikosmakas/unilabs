from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlencode
import requests
from models import (
    Student, Professor, db, init_app, LabGroup, CourseLab, RelGroupStudent,
    Coursename, RelCourseLab, RelLabGroup, RelLabStudent, StudentMissesPerGroup
)
from auth import (
    require_permission, require_role, audit_log, mask_pii, 
    transactional_enrollment, record_absence,
    get_academic_year, validate_registration_period, check_group_capacity,
    get_student_lab_status, check_existing_enrollment,
    register_student_to_lab, change_student_group, get_student_enrollments,
    STATUS_IN_PROGRESS, STATUS_FAILED, STATUS_COMPLETED
)
import os
from dotenv import load_dotenv
from datetime import datetime

# Φόρτωση μεταβλητών περιβάλλοντος
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-123')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'labregister.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['AUTH_MODE'] = os.getenv('AUTH_MODE', 'dev')
init_app(app)

AUTH_MODE = app.config['AUTH_MODE']

FAKE_USERS = {
    'student1': {
        'name': 'Test Student',
        'role': 'student',
        'am': '13628',
        'email': 'student1@test.gr'
    },
    'prof1': {
        'name': 'Test Professor', 
        'role': 'professor',
        'prof_id': '1',
        'email': 'prof1@test.gr'
    },
    'admin1': {
        'name': 'Test Admin',
        'role': 'admin', 
        'admin_id': '1',
        'email': 'admin1@test.gr'
    }
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_group_occupancy(group_id, lab_id):
    """Υπολογισμός πληρότητας τμήματος"""
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
    """
    Λήψη ειδοποιήσεων για φοιτητή (απουσίες).
    Αντίστοιχο του createNtfs στο παλιό project.
    """
    academic_year = get_academic_year()
    notifications = []
    
    # Λήψη εγγραφών με απουσίες
    enrollments = get_student_enrollments(student_am, academic_year)
    
    for e in enrollments:
        if e['absences'] and e['absences'] != '-':
            # Μέτρηση απουσιών
            absence_count = len(e['absences'].split(',')) if isinstance(e['absences'], str) else 0
            
            # Λήψη max_misses από το εργαστήριο
            lab = CourseLab.query.get(e['lab_id'])
            max_misses = lab.max_misses if lab else 3
            
            if absence_count > 0:
                notifications.append({
                    'type': 'warning' if absence_count >= max_misses - 1 else 'info',
                    'lab_name': e['lab_name'],
                    'message': f"Έχετε {absence_count} απουσίες στο {e['lab_name']}",
                    'absences': absence_count,
                    'max_absences': max_misses,
                    'is_critical': absence_count >= max_misses
                })
    
    return notifications

def create_or_get_student(am, name, email=None):
    """
    Δημιουργία ή λήψη φοιτητή από τη βάση.
    Αντίστοιχο του CheckUserRegistration στο παλιό project.
    """
    student = Student.query.filter_by(am=am).first()
    
    if student:
        return student, False  # exists
    
    # Δημιουργία νέου φοιτητή
    new_student = Student(
        am=am,
        name=name,
        semester=1,  # Default semester
        pwd='',  # Δεν χρησιμοποιείται με CAS
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
        
        return new_student, True  # created
    except Exception as e:
        db.session.rollback()
        return None, False

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Authentication required', 'message': error.description}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Insufficient permissions', 'message': error.description}), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

# =============================================================================
# CAS CONFIGURATION
# =============================================================================

CAS_LOGIN_URL = 'https://sso.uoi.gr/login'
CAS_VALIDATE_URL = 'https://sso.uoi.gr/serviceValidate'
SERVICE_URL = 'http://localhost:5000/cas_callback'

# =============================================================================
# AUTHENTICATION ROUTES
# =============================================================================

@app.route('/login')
def login():
    if app.config['AUTH_MODE'] == 'dev':
        return render_template('dev_login.html', users=FAKE_USERS)
    
    params = {'service': SERVICE_URL}
    return redirect(f"{CAS_LOGIN_URL}?{urlencode(params)}")

@app.route('/cas_callback')
def cas_callback():
    if app.config['AUTH_MODE'] == 'dev':
        username = request.args.get('username')
        if not username or username not in FAKE_USERS:
            return "Invalid development user", 400
        
        fake_user = FAKE_USERS[username]
        session['schGrAcPersonID'] = fake_user.get('am') or fake_user.get('prof_id') or fake_user.get('admin_id')
        session['role'] = fake_user['role']
        session['name'] = fake_user['name']
        
        audit_log('dev_login', new_value=f"Development user {username} logged in as {fake_user['role']}")
        return redirect(url_for('dashboard'))
    
    # PRODUCTION MODE: CAS Authentication
    ticket = request.args.get('ticket')
    if not ticket:
        return redirect(url_for('login'))

    params = {'service': SERVICE_URL, 'ticket': ticket}
    response = requests.get(CAS_VALIDATE_URL, params=params, verify=True)
    if response.status_code != 200 or 'authenticationSuccess' not in response.text:
        return "CAS authentication failed", 401

    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.text)
    ns = {'cas': 'http://www.yale.edu/tp/cas'}
    auth = root.find('.//cas:authenticationSuccess', ns)
    if auth is None:
        return "CAS authentication failed", 401

    # Extract CAS attributes
    schGrAcPersonID = auth.find('cas:schGrAcPersonID', ns)
    displayName = auth.find('cas:displayName', ns)
    eduPersonAffiliation = auth.find('cas:eduPersonAffiliation', ns)
    mail = auth.find('cas:mail', ns)
    
    schGrAcPersonID = schGrAcPersonID.text if schGrAcPersonID is not None else None
    displayName = displayName.text if displayName is not None else 'Unknown'
    affiliation = eduPersonAffiliation.text if eduPersonAffiliation is not None else ''
    email = mail.text if mail is not None else ''
    
    if not schGrAcPersonID:
        return "CAS authentication failed: No student ID", 401
    
    # Check if user is student
    if 'student' in affiliation.lower():
        # Create or get student
        student, created = create_or_get_student(schGrAcPersonID, displayName, email)
        
        if not student:
            return "Failed to create user account", 500
        
        session['schGrAcPersonID'] = schGrAcPersonID
        session['role'] = 'student'
        session['name'] = displayName
        session['email'] = email
        
        if created:
            audit_log('cas_first_login', new_value=f"New student {schGrAcPersonID} created")
    
    elif 'faculty' in affiliation.lower() or 'staff' in affiliation.lower():
        # Check if professor exists
        prof = Professor.query.filter_by(email=email).first()
        if prof:
            session['schGrAcPersonID'] = str(prof.prof_id)
            session['role'] = 'professor'
            session['name'] = displayName
        else:
            return "Professor not registered in system", 403
    else:
        return "Unknown user affiliation", 403

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    audit_log('user_logout', reason='User logged out')
    session.clear()
    return redirect(url_for('login'))

# =============================================================================
# DASHBOARD ROUTE
# =============================================================================

@app.route('/dashboard')
@require_permission('dashboard', 'view')
def dashboard():
    """Dashboard με όλα τα δεδομένα για τα tabs"""
    academic_year = get_academic_year()
    
    labs = CourseLab.query.all()
    
    groups_raw = db.session.query(LabGroup, RelLabGroup.lab_id).join(
        RelLabGroup, LabGroup.group_id == RelLabGroup.group_id
    ).filter(LabGroup.year == academic_year).all()
    
    groups = []
    for group, lab_id in groups_raw:
        occupancy = get_group_occupancy(group.group_id, lab_id)
        groups.append({
            'group_id': group.group_id,
            'daytime': group.daytime,
            'year': group.year,
            'lab_id': lab_id,
            'occupancy_percentage': occupancy['percentage'],
            'available_spots': occupancy['available'],
            'is_full': occupancy['is_full']
        })
    
    students = Student.query.all() if session.get('role') in ['professor', 'admin'] else []
    professors = Professor.query.all()
    registrations = RelLabStudent.query.all() if session.get('role') in ['professor', 'admin'] else []
    absences = StudentMissesPerGroup.query.all() if session.get('role') in ['professor', 'admin'] else []
    
    # Εγγραφές και ειδοποιήσεις του τρέχοντος φοιτητή
    student_enrollments = []
    notifications = []
    if session.get('role') == 'student':
        student_am = session.get('schGrAcPersonID')
        student_enrollments = get_student_enrollments(student_am, academic_year)
        notifications = get_student_notifications(student_am)
    
    return render_template('dashboard.html', 
                         name=session.get('name', 'Guest'), 
                         role=session.get('role', 'guest'),
                         AUTH_MODE=app.config['AUTH_MODE'],
                         academic_year=academic_year,
                         labs=labs,
                         groups=groups,
                         students=students,
                         professors=professors,
                         registrations=registrations,
                         absences=absences,
                         student_enrollments=student_enrollments,
                         notifications=notifications)

# =============================================================================
# PHASE 1: CASCADING DATA APIs
# =============================================================================

@app.route('/api/semesters')
@require_permission('dashboard', 'view')
def get_semesters():
    """Λήψη διαθέσιμων εξαμήνων"""
    semesters = db.session.query(Coursename.semester).distinct().order_by(Coursename.semester).all()
    
    return jsonify({
        'success': True,
        'data': [{'id': s.semester, 'name': f'{s.semester}'} for s in semesters]
    })

@app.route('/api/courses/<semester>')
@require_permission('dashboard', 'view')
def get_courses_by_semester(semester):
    """Λήψη μαθημάτων για συγκεκριμένο εξάμηνο"""
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

@app.route('/api/labs/<int:course_id>')
@require_permission('dashboard', 'view')
def get_labs_by_course(course_id):
    """Λήψη εργαστηρίων για συγκεκριμένο μάθημα"""
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

@app.route('/api/groups/<int:lab_id>')
@require_permission('dashboard', 'view')
def get_groups_by_lab(lab_id):
    """Λήψη τμημάτων για συγκεκριμένο εργαστήριο"""
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

@app.route('/api/academic-year')
@require_permission('dashboard', 'view')
def get_current_academic_year():
    """Επιστροφή τρέχοντος ακαδημαϊκού έτους"""
    return jsonify({
        'success': True,
        'academic_year': get_academic_year(),
        'calculated_at': datetime.now().isoformat()
    })

# =============================================================================
# PHASE 2: REGISTRATION APIs
# =============================================================================

@app.route('/api/register-lab', methods=['POST'])
@require_permission('registrations', 'create')
def api_register_lab():
    """Εγγραφή φοιτητή σε εργαστήριο και τμήμα"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Δεν δόθηκαν δεδομένα'}), 400
    
    lab_id = data.get('lab_id')
    group_id = data.get('group_id')
    
    if not lab_id or not group_id:
        return jsonify({'success': False, 'message': 'Επιλέξτε Τμήμα'}), 400
    
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    success, message, details = register_student_to_lab(student_am, lab_id, group_id)
    
    if success:
        return jsonify({'success': True, 'message': message, 'details': details}), 200
    else:
        return jsonify({'success': False, 'message': message, 'details': details}), 400

@app.route('/api/change-group', methods=['PUT'])
@require_permission('registrations', 'create')
def api_change_group():
    """Αλλαγή τμήματος φοιτητή"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'Δεν δόθηκαν δεδομένα'}), 400
    
    lab_id = data.get('lab_id')
    old_group_id = data.get('old_group_id')
    new_group_id = data.get('new_group_id')
    
    if not all([lab_id, old_group_id, new_group_id]):
        return jsonify({'success': False, 'message': 'Λείπουν απαραίτητα πεδία'}), 400
    
    if old_group_id == new_group_id:
        return jsonify({'success': False, 'message': 'Επιλέξτε διαφορετικό τμήμα'}), 400
    
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    success, message, details = change_student_group(student_am, old_group_id, new_group_id, lab_id)
    
    if success:
        return jsonify({'success': True, 'message': message, 'details': details}), 200
    else:
        return jsonify({'success': False, 'message': message, 'details': details}), 400

@app.route('/api/student/enrollments')
@require_permission('registrations', 'view')
def api_student_enrollments():
    """Λήψη εγγραφών τρέχοντος φοιτητή"""
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    year = request.args.get('year', type=int, default=get_academic_year())
    enrollments = get_student_enrollments(student_am, year)
    
    return jsonify({
        'success': True,
        'academic_year': year,
        'data': enrollments
    })

@app.route('/api/student/enrollment-status/<int:lab_id>')
@require_permission('registrations', 'view')
def api_enrollment_status(lab_id):
    """Έλεγχος κατάστασης εγγραφής φοιτητή σε συγκεκριμένο εργαστήριο"""
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

@app.route('/api/groups/<int:group_id>/professor')
@require_permission('professors_list', 'view')
def api_group_professor(group_id):
    """Λήψη στοιχείων υπεύθυνου καθηγητή για τμήμα"""
    from models import RelGroupProf
    
    professors = db.session.query(Professor).join(
        RelGroupProf, Professor.prof_id == RelGroupProf.prof_id
    ).filter(RelGroupProf.group_id == group_id).all()
    
    if not professors:
        return jsonify({
            'success': False,
            'message': 'Δεν βρέθηκε υπεύθυνος εργαστηρίου'
        }), 404
    
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

# =============================================================================
# PHASE 4: STUDENT PROFILE & NOTIFICATIONS APIs
# =============================================================================

@app.route('/api/student/profile', methods=['GET'])
@require_permission('students_list', 'view_own_profile')
def api_get_student_profile():
    """Λήψη προφίλ τρέχοντος φοιτητή"""
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

@app.route('/api/student/profile', methods=['PUT'])
@require_permission('students_list', 'edit')
def api_update_student_profile():
    """
    Ενημέρωση προφίλ φοιτητή.
    Αντίστοιχο του update_email στο παλιό project.
    """
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Δεν δόθηκαν δεδομένα'}), 400
    
    student = Student.query.get(student_am)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found'}), 404
    
    # Validation
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    semester = data.get('semester')
    
    if name and len(name) < 3:
        return jsonify({'success': False, 'message': 'Δώστε Ονοματεπώνυμο'}), 400
    
    if email and '@' not in email:
        return jsonify({'success': False, 'message': 'Εισάγετε έγκυρο email'}), 400
    
    if semester is not None:
        try:
            semester = int(semester)
            if semester < 1 or semester > 12:
                return jsonify({'success': False, 'message': 'Δώστε το εξάμηνο σπουδών με αριθμό (1-12)'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Δώστε το εξάμηνο σπουδών με αριθμό'}), 400
    
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
        audit_log(
            'profile_updated',
            old_value=old_values,
            new_value=new_values,
            reason="Student updated profile"
        )
        
        return jsonify({
            'success': True,
            'message': 'Το προφίλ ενημερώθηκε επιτυχώς',
            'data': {
                'am': student.am,
                'name': student.name,
                'semester': student.semester,
                'email': student.email
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Σφάλμα στην ενημέρωση'}), 500

@app.route('/api/student/notifications')
@require_permission('absences', 'view_own')
def api_student_notifications():
    """Λήψη ειδοποιήσεων φοιτητή (απουσίες)"""
    student_am = session.get('schGrAcPersonID')
    if not student_am:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    notifications = get_student_notifications(student_am)
    
    return jsonify({
        'success': True,
        'count': len(notifications),
        'data': notifications
    })

# =============================================================================
# EXISTING ROUTES (Groups, Absences, Profile, Professors)
# =============================================================================

@app.route('/groups')
@require_permission('groups', 'view')
def list_groups():
    """List lab groups with PII masking"""
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

@app.route('/groups/<int:group_id>/join', methods=['POST'])
@require_permission('groups', 'join')
def join_group(group_id):
    """Join group with transactional safety and preconditions check"""
    student_am = session['schGrAcPersonID']
    success, message = transactional_enrollment(student_am, group_id)
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/groups/<int:group_id>/leave', methods=['POST'])
@require_permission('groups', 'leave')
def leave_group(group_id):
    """Leave group with audit trail"""
    student_am = session['schGrAcPersonID']
    
    try:
        enrollment = RelGroupStudent.query.filter_by(
            am=student_am, group_id=group_id
        ).first()
        
        if not enrollment:
            return jsonify({'success': False, 'message': 'Not enrolled in this group'}), 400
        
        audit_log(
            'enrollment_deleted',
            old_value=f"Student {student_am} was enrolled in group {group_id}",
            reason='Student left group'
        )
        
        db.session.delete(enrollment)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Successfully left group'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to leave group'}), 500

@app.route('/groups/<int:group_id>/absences', methods=['GET'])
@require_permission('absences', 'view_group')
def view_group_absences(group_id):
    """View absences for a group (professors/admins only)"""
    absences = StudentMissesPerGroup.query.filter_by(group_id=group_id).all()
    absences_data = []
    
    for absence in absences:
        student = Student.query.get(absence.am)
        absence_dict = {
            'student_am': mask_pii({'am': absence.am})['am'],
            'student_name': student.name if student else 'Unknown',
            'date': absence.misses
        }
        absences_data.append(absence_dict)
    
    return jsonify(absences_data)

@app.route('/groups/<int:group_id>/absences', methods=['POST'])
@require_permission('absences', 'edit_group_absences')
def record_group_absence(group_id):
    """Record absence for a student (professors/admins only)"""
    data = request.get_json()
    student_am = data.get('student_am')
    date = data.get('date')
    reason = data.get('reason')
    
    if not student_am or not date:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    success, message = record_absence(student_am, group_id, date, reason)
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/students/profile')
@require_permission('students_list', 'view_own_profile')
def view_own_profile():
    """View own student profile with PII masking"""
    student_am = session['schGrAcPersonID']
    student = Student.query.get(student_am)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    profile = mask_pii({
        'am': student.am,
        'name': student.name,
        'semester': student.semester,
        'email': student.email
    })
    
    return jsonify(profile)

@app.route('/professors')
@require_permission('professors_list', 'view')
def list_professors():
    """List professors with PII masking"""
    professors = Professor.query.all()
    professors_data = []
    
    for prof in professors:
        prof_dict = {
            'prof_id': prof.prof_id,
            'name': prof.name,
            'status': prof.status,
            'office': prof.office,
            'email': prof.email,
            'tel': prof.tel
        }
        professors_data.append(mask_pii(prof_dict))
    
    return jsonify(professors_data)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True)