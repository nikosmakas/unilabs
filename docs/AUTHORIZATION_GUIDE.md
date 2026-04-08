# Authorization System Guide

## Overview
This system implements **server-side authorization** based on the `permission_matrix.json` file. All permission checks are enforced at the server level - frontend visibility is only for UX purposes.

## Key Principles

### 1. Server-Side Authorization Only
- **All permission checks happen server-side** using decorators
- Frontend hiding/showing buttons is purely UX - not security
- Every endpoint validates permissions before processing requests

### 2. Role-Based Access Control (RBAC)
Roles: `guest`, `student`, `professor`, `admin`

### 3. Resource-Action Permissions
Each resource (e.g., `groups`, `absences`) has specific actions (e.g., `view`, `create`, `edit`) that are allowed for specific roles.

## Implementation Details

### Permission Matrix Structure
```json
{
  "roles": ["guest", "student", "professor", "admin"],
  "resources": {
    "groups": {
      "view": ["guest", "student", "professor", "admin"],
      "join": ["student"],
      "leave": ["student"],
      "create": ["professor", "admin"],
      "edit": ["professor", "admin"],
      "delete": ["professor", "admin"]
    }
  }
}
```

### Decorators

#### `@require_permission(resource, action)`
Checks if user has permission for specific resource.action:
```python
@app.route('/groups')
@require_permission('groups', 'view')
def list_groups():
    # Only executes if user has 'groups.view' permission
```

#### `@require_role(*roles)`
Checks if user has one of the specified roles:
```python
@app.route('/admin/users')
@require_role('admin')
def admin_users():
    # Only executes if user is admin
```

## Critical Security Features

### 1. Transactional Enrollment with Preconditions
```python
def transactional_enrollment(student_am, group_id):
    # 1. Start database transaction
    # 2. Check enrollment preconditions (enrolled in course, capacity available)
    # 3. Verify not already enrolled
    # 4. Create enrollment record
    # 5. Commit transaction
    # 6. Log audit trail
```

**Preconditions Check:**
- Student must be enrolled in the related course
- Group must have available capacity
- Student must not already be enrolled

### 2. Audit Logging
All critical actions are logged with:
- Timestamp
- User ID and role
- Action performed
- IP address
- Old/new values (for modifications)
- Reason for action

```python
audit_log(
    action="enrollment_created",
    new_value=f"Student {student_am} enrolled in group {group_id}",
    reason="Student initiated enrollment"
)
```

### 3. PII Masking
Personal Identifiable Information is masked in public views:
- **Email**: `user@domain.com` → `us***@domain.com`
- **AM/Phone**: `123456789` → `12***89`

```python
def mask_pii(data, fields_to_mask=['email', 'am', 'tel']):
    # Masks sensitive fields before returning to client
```

### 4. Absence Recording with Authorization
Only professors/admins can record absences:
```python
def record_absence(student_am, group_id, date, reason=None):
    # 1. Check if user has professor/admin role
    # 2. Record absence in database
    # 3. Log audit trail with reason
```

## Database Transaction Safety

### Enrollment Process
1. **Begin Transaction**
2. **Check Preconditions** (within transaction to prevent race conditions)
3. **Verify Capacity** (current enrollments < max capacity)
4. **Check Existing Enrollment** (prevent duplicates)
5. **Create Enrollment Record**
6. **Commit Transaction**
7. **Audit Log**

### Race Condition Prevention
Using database transactions ensures that:
- Two students can't simultaneously join a group that has only 1 spot left
- Enrollment counts are accurate
- No duplicate enrollments

## Error Handling

### Authorization Errors
- **401 Unauthorized**: User not authenticated
- **403 Forbidden**: User authenticated but lacks permission
- **404 Not Found**: Resource doesn't exist

### Business Logic Errors
- **400 Bad Request**: Invalid data or business rule violation
- **500 Internal Server Error**: System error

## Security Best Practices Implemented

1. **Principle of Least Privilege**: Users only get minimum required permissions
2. **Server-Side Validation**: All checks happen server-side
3. **Audit Trails**: All critical actions are logged
4. **PII Protection**: Sensitive data is masked in public views
5. **Transaction Safety**: Database operations are atomic
6. **Input Validation**: All inputs are validated before processing
7. **Error Handling**: Proper error responses without information leakage

## Testing Authorization

### Test Cases to Verify
1. **Student tries to access professor-only endpoint** → 403 Forbidden
2. **Guest tries to join group** → 401 Unauthorized
3. **Student joins full group** → 400 Bad Request
4. **Student joins group twice** → 400 Bad Request
5. **Professor records absence** → 200 Success + Audit Log
6. **Student tries to record absence** → 403 Forbidden

### Manual Testing
```bash
# Test student joining group
curl -X POST /groups/1/join -H "Cookie: session=..."

# Test professor viewing absences
curl -X GET /groups/1/absences -H "Cookie: session=..."

# Test unauthorized access
curl -X GET /admin/users -H "Cookie: session=..."
```

## Monitoring and Logging

### Audit Log Format
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "user_id": "13628",
  "user_role": "student",
  "action": "enrollment_created",
  "ip_address": "192.168.1.100",
  "new_value": "Student 13628 enrolled in group 1",
  "reason": "Student initiated enrollment"
}
```

### Log Analysis
- Monitor for failed authorization attempts
- Track enrollment patterns
- Identify potential security issues
- Compliance reporting

## Future Enhancements

1. **Rate Limiting**: Prevent abuse of endpoints
2. **Session Management**: Implement proper session handling
3. **CSRF Protection**: Add CSRF tokens to forms
4. **API Versioning**: Version API endpoints
5. **Caching**: Cache permission matrix for performance
6. **Real-time Notifications**: Notify users of enrollment changes

