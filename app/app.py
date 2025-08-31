from flask import Flask, redirect, request, session, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlencode
import requests
from models import User
import os
from dotenv import load_dotenv

# Φόρτωση μεταβλητών περιβάλλοντος
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-123')  # Use a secure key!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/labregister.sqlite'
db = SQLAlchemy(app)

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
    user = User.query.filter_by(id=schGrAcPersonID).first()
    if not user:
        return "User not registered", 403

    # Store session data
    session['schGrAcPersonID'] = schGrAcPersonID
    session['role'] = user.role
    session['name'] = displayName

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'schGrAcPersonID' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['name'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)