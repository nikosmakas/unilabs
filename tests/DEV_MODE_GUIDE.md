# Development Authentication Mode Guide

## 🔧 Overview

The development authentication mode allows testing the authorization system without real CAS credentials. This is **ONLY for development and testing purposes**.

## ⚠️ **SECURITY WARNING**

**NEVER enable development mode in production!** This mode bypasses all real authentication and uses hardcoded test users.

## 🚀 Quick Start

### 1. Enable Development Mode

Set the environment variable:
```bash
export AUTH_MODE=dev
```

Or create a `.env` file:
```bash
AUTH_MODE=dev
```

### 2. Start the Application

```bash
python app.py
```

### 3. Access Development Login

Navigate to `http://localhost:5000/login`

You'll see a development login page with available test users.

## 👥 Available Test Users

| Username | Role | Name | ID | Permissions |
|----------|------|------|----|-------------|
| `student1` | Student | Test Student | 13628 | View groups, join/leave groups, view own profile |
| `prof1` | Professor | Test Professor | 1 | Manage groups, view/edit absences, manage enrollments |
| `admin1` | Admin | Test Admin | 1 | Full access to all features including user management |

## 🔐 How It Works

### Development Mode Flow

1. **Login Page**: Shows a form with available test users
2. **User Selection**: Click on any user to "login"
3. **Session Creation**: Creates a session with the selected user's role
4. **Authorization**: All authorization checks work normally with the fake user's role

### Production Mode Flow

1. **Login Page**: Redirects to CAS authentication
2. **CAS Authentication**: Real university authentication
3. **Session Creation**: Creates session with real user data
4. **Authorization**: Same authorization system

## 🧪 Testing Authorization

### Testing Different Roles

1. **Login as Student**:
   - Can view groups ✅
   - Can join/leave groups ✅
   - Cannot access professor-only endpoints ❌
   - Cannot access admin-only endpoints ❌

2. **Login as Professor**:
   - Can view groups ✅
   - Can manage groups ✅
   - Can view/edit absences ✅
   - Cannot access admin-only endpoints ❌

3. **Login as Admin**:
   - Can access all features ✅
   - Can manage users ✅
   - Full system access ✅

### Testing Specific Endpoints

```bash
# Test student permissions
curl -X GET http://localhost:5000/groups
curl -X POST http://localhost:5000/groups/1/join
curl -X GET http://localhost:5000/groups/1/absences  # Should fail

# Test professor permissions
curl -X GET http://localhost:5000/groups/1/absences  # Should work
curl -X POST http://localhost:5000/groups/1/absences  # Should work

# Test admin permissions
curl -X GET http://localhost:5000/admin/users  # Should work
```

## 📁 File Structure

```
app/
├── app.py                    # Main application with dev mode logic
├── templates/
│   ├── dev_login.html       # Development login page
│   └── dashboard.html       # Updated with user info
└── auth.py                  # Authorization system (unchanged)
```

## 🔧 Configuration

### Environment Variables

```bash
# Development Mode
AUTH_MODE=dev

# Production Mode
AUTH_MODE=cas

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///data/labregister.sqlite

# Security
SECRET_KEY=your-secure-secret-key
```

### Fake Users Configuration

The fake users are defined in `app.py`:

```python
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
```

## 🧪 Testing

### Run Development Tests

```bash
python test_dev_auth.py
```

### Manual Testing

1. Start the application in dev mode
2. Navigate to `/login`
3. Select different users and test their permissions
4. Verify that authorization works correctly for each role

## 🔍 Monitoring

### Audit Logs

Development logins are logged for audit purposes:

```json
{
  "timestamp": "2024-01-15T10:30:00",
  "user_id": "13628",
  "user_role": "student",
  "action": "dev_login",
  "new_value": "Development user student1 logged in as student",
  "reason": null
}
```

### Session Data

Check session data in browser developer tools:
- `schGrAcPersonID`: User ID
- `role`: User role (student/professor/admin)
- `name`: User display name

## 🚨 Security Considerations

### What Development Mode Does

✅ **Safe for Development**:
- Bypasses CAS authentication
- Uses hardcoded test users
- Maintains full authorization system
- Logs all actions for audit

❌ **Never Use in Production**:
- No real authentication
- Hardcoded credentials
- Bypasses security measures
- Could expose sensitive data

### Production Checklist

Before deploying to production:

- [ ] Set `AUTH_MODE=cas`
- [ ] Remove any dev mode environment variables
- [ ] Verify CAS authentication is working
- [ ] Test with real university credentials
- [ ] Review audit logs for any dev mode usage

## 🐛 Troubleshooting

### Common Issues

1. **Dev mode not working**:
   - Check `AUTH_MODE=dev` environment variable
   - Restart the application
   - Clear browser cache

2. **Authorization not working**:
   - Verify user role is set correctly in session
   - Check permission matrix configuration
   - Review audit logs

3. **Session issues**:
   - Clear browser cookies
   - Check `SECRET_KEY` configuration
   - Verify session storage

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Related Documentation

- [Authorization System Guide](AUTHORIZATION_GUIDE.md)
- [Test Summary](TEST_SUMMARY.md)
- [Permission Matrix](app/templates/permission_matrix.json)

---

**Remember**: Development mode is a tool for testing, not for production use!
