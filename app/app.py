from flask import Flask, session, jsonify, render_template
from models import db, init_app
from auth import get_academic_year
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-123')
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'labregister.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['AUTH_MODE'] = os.getenv('AUTH_MODE', 'dev')
init_app(app)

with app.app_context():
    db.create_all()

# =============================================================================
# CONTEXT PROCESSOR
# =============================================================================

@app.context_processor
def inject_common_vars():
    """Inject common template variables into all templates."""
    return {
        'name': session.get('name', 'Guest'),
        'role': session.get('role', 'guest'),
        'AUTH_MODE': app.config['AUTH_MODE'],
        'academic_year': get_academic_year(),
    }

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
    return render_template('404.html', active_page=''), 404

# =============================================================================
# REGISTER BLUEPRINTS
# =============================================================================

from routes.auth_routes import auth_bp
from routes.views import views_bp
from routes.api import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(views_bp)
app.register_blueprint(api_bp)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True)