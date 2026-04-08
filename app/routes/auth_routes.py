from flask import Blueprint, redirect, request, session, url_for, render_template, current_app
from urllib.parse import urlencode
import requests as http_requests

from models import Student, Professor
from auth import audit_log
from helpers import create_or_get_student

auth_bp = Blueprint('auth_bp', __name__)

FAKE_USERS = {
    'student1': {
        'name': 'Test Student (Dev)',
        'role': 'student',
        'am': '13628',
        'email': 'test.student@example.com'
    },
    'student2': {
        'name': 'Αλεξίου Μαρία',
        'role': 'student',
        'am': '10001',
        'email': 'malexiou@student.uoi.gr'
    },
    'prof1': {
        'name': 'Παπαδόπουλος Νίκος',
        'role': 'professor',
        'prof_id': '101',
        'email': 'npapadopoulos@uoi.gr'
    },
    'prof2': {
        'name': 'Αντωνίου Ελένη',
        'role': 'professor',
        'prof_id': '102',
        'email': 'eantonioiu@uoi.gr'
    },
    'admin1': {
        'name': 'System Administrator',
        'role': 'admin',
        'admin_id': '999',
        'email': 'admin@uoi.gr'
    }
}

# CAS configuration
CAS_LOGIN_URL = 'https://sso.uoi.gr/login'
CAS_VALIDATE_URL = 'https://sso.uoi.gr/serviceValidate'
SERVICE_URL = 'http://localhost:5000/cas_callback'


@auth_bp.route('/')
def index():
    """Default landing page - redirect to login."""
    if 'schGrAcPersonID' in session:
        return redirect(url_for('views_bp.dashboard'))
    return redirect(url_for('auth_bp.login'))


@auth_bp.route('/login')
def login():
    if current_app.config['AUTH_MODE'] == 'dev':
        return render_template('dev_login.html', users=FAKE_USERS)

    params = {'service': SERVICE_URL}
    return redirect(f"{CAS_LOGIN_URL}?{urlencode(params)}")


@auth_bp.route('/cas_callback')
def cas_callback():
    if current_app.config['AUTH_MODE'] == 'dev':
        username = request.args.get('username')
        if not username or username not in FAKE_USERS:
            return "Invalid development user", 400

        fake_user = FAKE_USERS[username]
        session['schGrAcPersonID'] = fake_user.get('am') or fake_user.get('prof_id') or fake_user.get('admin_id')
        session['role'] = fake_user['role']
        session['name'] = fake_user['name']

        audit_log('dev_login', new_value=f"Development user {username} logged in as {fake_user['role']}")
        return redirect(url_for('views_bp.dashboard'))

    # PRODUCTION MODE: CAS Authentication
    ticket = request.args.get('ticket')
    if not ticket:
        return redirect(url_for('auth_bp.login'))

    params = {'service': SERVICE_URL, 'ticket': ticket}
    response = http_requests.get(CAS_VALIDATE_URL, params=params, verify=True)
    if response.status_code != 200 or 'authenticationSuccess' not in response.text:
        return "CAS authentication failed", 401

    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.text)
    ns = {'cas': 'http://www.yale.edu/tp/cas'}
    auth = root.find('.//cas:authenticationSuccess', ns)
    if auth is None:
        return "CAS authentication failed", 401

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

    if 'student' in affiliation.lower():
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
        prof = Professor.query.filter_by(email=email).first()
        if prof:
            session['schGrAcPersonID'] = str(prof.prof_id)
            session['role'] = 'professor'
            session['name'] = displayName
        else:
            return "Professor not registered in system", 403
    else:
        return "Unknown user affiliation", 403

    return redirect(url_for('views_bp.dashboard'))


@auth_bp.route('/logout')
def logout():
    audit_log('user_logout', reason='User logged out')
    session.clear()
    return redirect(url_for('auth_bp.login'))
