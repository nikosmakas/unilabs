import unittest
import json
import tempfile
import os
from datetime import datetime
from app.app import app
from app.auth import PermissionMatrix, require_permission, require_role, audit_log, mask_pii, transactional_enrollment, record_absence
from app.models import db, Student, Professor, LabGroup, CourseLab, RelGroupStudent, StudentMissesPerGroup, RelLabGroup
from flask import session

class TestAuthorizationSystem(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Initialize database with test config
        db.init_app(app)
        
        # Create database tables
        with app.app_context():
            db.create_all()
        
        # Create test data
        with app.app_context():
            self.create_test_data()
        
        # Create temporary permission matrix for testing
        self.create_test_permission_matrix()
    
    def tearDown(self):
        """Clean up after tests"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
        self.app_context.pop()
        if os.path.exists('test_permission_matrix.json'):
            os.remove('test_permission_matrix.json')
    
    def create_test_data(self):
        """Create test data in database"""
        # Create test student
        student = Student(
            am=13628,
            name='Test Student',
            semester=2,
            pwd='test123',
            email='test@student.gr'
        )
        db.session.add(student)
        
        # Create test professor
        professor = Professor(
            prof_id=1,
            name='Test Professor',
            status='Καθηγητής',
            office='Γραφείο 101',
            email='prof@uoi.gr',
            tel='2681050448'
        )
        db.session.add(professor)
        
        # Create test lab
        lab = CourseLab(
            lab_id=1,
            name='Test Lab',
            description='Test Lab Description',
            maxusers=10,
            reg_limit='2024-12-31',
            max_misses=2
        )
        db.session.add(lab)
        
        # Create test group
        group = LabGroup(
            group_id=1,
            daytime='Δευτέρα 10-12',
            year=2024,
            finalize=''
        )
        db.session.add(group)
        
        # Create lab-group relationship
        lab_group = RelLabGroup(
            lab_id=1,
            group_id=1
        )
        db.session.add(lab_group)
        
        db.session.commit()
    
    def create_test_permission_matrix(self):
        """Create test permission matrix file"""
        matrix = {
            "roles": ["guest", "student", "professor", "admin"],
            "resources": {
                "dashboard": {
                    "view": ["guest", "student", "professor", "admin"]
                },
                "groups": {
                    "view": ["guest", "student", "professor", "admin"],
                    "join": ["student"],
                    "leave": ["student"],
                    "create": ["professor", "admin"],
                    "edit": ["professor", "admin"],
                    "delete": ["professor", "admin"]
                },
                "absences": {
                    "view_group": ["professor", "admin"],
                    "edit_group_absences": ["professor", "admin"]
                },
                "students_list": {
                    "view_own_profile": ["student"]
                },
                "professors_list": {
                    "view": ["guest", "student", "professor", "admin"]
                }
            }
        }
        
        with open('test_permission_matrix.json', 'w', encoding='utf-8') as f:
            json.dump(matrix, f, indent=2)
    
    def test_permission_matrix_loading(self):
        """Test permission matrix loading"""
        matrix = PermissionMatrix()
        self.assertIsNotNone(matrix.matrix)
        self.assertIn('roles', matrix.matrix)
        self.assertIn('resources', matrix.matrix)
    
    def test_permission_checking(self):
        """Test permission checking logic"""
        matrix = PermissionMatrix()
        
        # Test valid permissions
        self.assertTrue(matrix.has_permission('student', 'groups', 'join'))
        self.assertTrue(matrix.has_permission('professor', 'groups', 'create'))
        self.assertTrue(matrix.has_permission('admin', 'groups', 'delete'))
        
        # Test invalid permissions
        self.assertFalse(matrix.has_permission('student', 'groups', 'create'))
        self.assertFalse(matrix.has_permission('guest', 'groups', 'join'))
        self.assertFalse(matrix.has_permission('professor', 'nonexistent', 'view'))
    
    def test_pii_masking(self):
        """Test PII masking functionality"""
        test_data = {
            'email': 'test@example.com',
            'am': 13628,
            'tel': '2681050448',
            'name': 'Test User'
        }
        
        masked = mask_pii(test_data)
        
        # Check email masking
        self.assertIn('***', masked['email'])
        self.assertNotEqual(masked['email'], test_data['email'])
        
        # Check AM masking
        self.assertIn('***', str(masked['am']))
        self.assertNotEqual(masked['am'], test_data['am'])
        
        # Check phone masking
        self.assertIn('***', str(masked['tel']))
        self.assertNotEqual(masked['tel'], test_data['tel'])
        
        # Check non-PII fields unchanged
        self.assertEqual(masked['name'], test_data['name'])
    
    def test_enrollment_preconditions(self):
        """Test enrollment preconditions checking"""
        from app.auth import check_enrollment_preconditions
        
        # Test valid enrollment
        can_join, message = check_enrollment_preconditions(13628, 1)
        self.assertTrue(can_join)
        self.assertEqual(message, "Eligible to join")
        
        # Test non-existent group
        can_join, message = check_enrollment_preconditions(13628, 999)
        self.assertFalse(can_join)
        self.assertEqual(message, "Group not found")
    
    def test_transactional_enrollment(self):
        """Test transactional enrollment"""
        # Test successful enrollment
        success, message = transactional_enrollment(13628, 1)
        self.assertTrue(success)
        self.assertEqual(message, "Enrollment successful")
        
        # Verify enrollment was created
        enrollment = RelGroupStudent.query.filter_by(am=13628, group_id=1).first()
        self.assertIsNotNone(enrollment)
        
        # Test duplicate enrollment
        success, message = transactional_enrollment(13628, 1)
        self.assertFalse(success)
        self.assertEqual(message, "Already enrolled")
    
    def test_absence_recording(self):
        """Test absence recording with authorization"""
        # Set up session for professor
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 1
            sess['role'] = 'professor'
        
        # Test successful absence recording
        success, message = record_absence(13628, 1, '2024-01-15', 'Test absence')
        self.assertTrue(success)
        self.assertEqual(message, "Absence recorded")
        
        # Verify absence was recorded
        absence = StudentMissesPerGroup.query.filter_by(am=13628, group_id=1).first()
        self.assertIsNotNone(absence)
        self.assertEqual(absence.misses, '2024-01-15')
    
    def test_unauthorized_absence_recording(self):
        """Test that students cannot record absences"""
        # Set up session for student
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 13628
            sess['role'] = 'student'
        
        # Test unauthorized absence recording
        success, message = record_absence(13628, 1, '2024-01-15')
        self.assertFalse(success)
        self.assertEqual(message, "Insufficient permissions to record absence")
    
    def test_endpoint_authorization(self):
        """Test endpoint authorization"""
        # Test unauthorized access to groups endpoint
        response = self.app.get('/groups')
        self.assertEqual(response.status_code, 401)  # Unauthorized
        
        # Test authorized access with student session
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 13628
            sess['role'] = 'student'
        
        response = self.app.get('/groups')
        self.assertEqual(response.status_code, 200)  # Authorized
    
    def test_join_group_endpoint(self):
        """Test join group endpoint"""
        # Set up student session
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 13628
            sess['role'] = 'student'
        
        # Test successful join
        response = self.app.post('/groups/1/join')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Test joining again (should fail)
        response = self.app.post('/groups/1/join')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_leave_group_endpoint(self):
        """Test leave group endpoint"""
        # First enroll the student
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 13628
            sess['role'] = 'student'
        
        self.app.post('/groups/1/join')
        
        # Test successful leave
        response = self.app.post('/groups/1/leave')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Test leaving again (should fail)
        response = self.app.post('/groups/1/leave')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
    
    def test_absences_endpoint_authorization(self):
        """Test absences endpoint authorization"""
        # Test student trying to view absences (should fail)
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 13628
            sess['role'] = 'student'
        
        response = self.app.get('/groups/1/absences')
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test professor viewing absences (should succeed)
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 1
            sess['role'] = 'professor'
        
        response = self.app.get('/groups/1/absences')
        self.assertEqual(response.status_code, 200)  # Authorized
    
    def test_audit_logging(self):
        """Test audit logging functionality"""
        # Set up session
        with self.app.session_transaction() as sess:
            sess['schGrAcPersonID'] = 13628
            sess['role'] = 'student'
        
        # Test audit log creation
        audit_log(
            action="test_action",
            old_value="old",
            new_value="new",
            reason="test reason"
        )
        
        # Note: In a real test, you would capture and verify the log output
        # For now, we just test that the function doesn't raise an exception
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
