from flask import Flask, redirect, request, session, url_for, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlencode
import requests
from app.models import Student, Professor, db, init_app, LabGroup, CourseLab, RelGroupStudent
from app.auth import require_permission, require_role, audit_log, mask_pii, transactional_enrollment, record_absence
import os
from dotenv import load_dotenv

# Φόρτωση μεταβλητών περιβάλλοντος
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-123')  # Use a secure key!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/labregister.sqlite'
init_app(app)

# Error handlers for authorization
@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Authentication required', 'message': error.description}), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Insufficient permissions', 'message': error.description}), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

CAS_LOGIN_URL = 'https://sso.uoi.gr/login'
CAS_VALIDATE_URL = 'https://sso.uoi.gr/serviceValidate'
SERVICE_URL = 'http://localhost:5000/cas_callback'

@app.route('/login')
def login():
    params = {
        'service': SERVICE_URL
    }
    return redirect(f"{CAS_LOGIN_URL}?{urlencode(params)}")

@app.route('/cas_callback')
def cas_callback():
    ticket = request.args.get('ticket')
    if not ticket:
        return redirect(url_for('login'))

    # Validate ticket with CAS
    params = {
        'service': SERVICE_URL,
        'ticket': ticket
    }
    response = requests.get(CAS_VALIDATE_URL, params=params, verify=True)
    if response.status_code != 200 or 'authenticationSuccess' not in response.text:
        return "CAS authentication failed", 401

    # Parse CAS XML response
    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.text)
    ns = {'cas': 'http://www.yale.edu/tp/cas'}
    auth = root.find('.//cas:authenticationSuccess', ns)
    if auth is None:
        return "CAS authentication failed", 401

    schGrAcPersonID = auth.find('cas:schGrAcPersonID', ns).text
    displayName = auth.find('cas:displayName', ns).text
    eduPersonAffiliation = auth.find('cas:eduPersonAffiliation', ns).text

    # Check user in DB
    user = Student.query.filter_by(am=schGrAcPersonID).first()
    if not user:
        return "User not registered", 403

    # Store session data
    session['schGrAcPersonID'] = schGrAcPersonID
    session['role'] = 'student'  # Default role for students
    session['name'] = displayName

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@require_permission('dashboard', 'view')
def dashboard():
    return render_template('dashboard.html', name=session['name'], role=session['role'])

@app.route('/logout')
def logout():
    audit_log('user_logout', reason='User logged out')
    session.clear()
    return redirect(url_for('login'))

# Groups endpoints with server-side authorization
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
        
        # Audit before deletion
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
    from app.models import StudentMissesPerGroup
    
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
    
    # Mask PII for public view
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

if __name__ == '__main__':
    app.run(debug=True)