# UniLabs - Σύστημα Διαχείρισης Εργαστηρίων

Διαδικτυακή εφαρμογή για τη διαχείριση εργαστηρίων και εγγραφών φοιτητών.

## 📁 Δομή Project
thesis/unilabs/
├── app/                            # Flask Application Root
│   ├── data/
│   │   ├── labregister.sqlite      # SQLite Database
│   │   └── data_labregister.sql    # Schema Backup & Initial Data
│   ├── templates/
│   │   ├── dashboard.html          # Main User Interface
│   │   ├── dev_login.html          # Developer Mode Login Page
│   │   ├── login.html              # Production Login Page
│   │   └── permission_matrix.json  # Role-based Access Control (RBAC) Mapping
│   ├── app.py                      # Main Entry Point & API Routes
│   ├── auth.py                     # Authorization & Registration Logic
│   ├── models.py                   # SQLAlchemy Database Models
│   ├── requirements.txt            # Python Dependencies
│   ├── run_tests.py                # Automated Testing Suite
│   └── TESTING_CHECKLIST.md        # Manual Testing & QA Guide
│
├── tests/
│   ├── DEV_MODE_GUIDE.md           # Documentation for Developer Mode
│   ├── AUTHORIZATION_GUIDE.md      # Detailed Authorization Docs
│   └── test_dev_auth.py            # Authentication & Security Tests
│
├── previous_project_blueprint.json # Reference from LabRegFrontCas
└── README.md                       # Project Documentation

## 🚀 Γρήγορη Εκκίνηση

### 1. Εγκατάσταση

cd thesis/unilabs/app pip install -r requirements.txt

### 2. Ενημέρωση Test Data

python run_tests.py

### 3. Εκκίνηση Server

python app.py

### 4. Πρόσβαση
Άνοιξε: **http://localhost:5000/login**

## 🔐 Development Mode

Για testing χωρίς CAS authentication:

| User | Role | Description |
|------|------|-------------|
| `student1` | Φοιτητής | AM: 13628 |
| `prof1` | Καθηγητής | Prof ID: 1 |
| `admin1` | Διαχειριστής | Full access |

> Ενεργοποίηση: `AUTH_MODE=dev` στο environment

## ✨ Features

### Για Φοιτητές
- ✅ Εγγραφή σε εργαστήριο (cascading dropdowns)
- ✅ Αλλαγή τμήματος
- ✅ Προβολή εγγραφών & απουσιών
- ✅ Ενημέρωση προφίλ

### Για Καθηγητές/Admins
- ✅ Προβολή όλων των εγγραφών
- ✅ Διαχείριση απουσιών
- ✅ Προβολή φοιτητών

### Σύστημα
- ✅ Role-based access control
- ✅ Audit logging
- ✅ Registration period validation
- ✅ Group capacity management
- ✅ Dark/Light theme

## 🔧 APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/semesters` | GET | Λίστα εξαμήνων |
| `/api/courses/<semester>` | GET | Μαθήματα ανά εξάμηνο |
| `/api/labs/<course_id>` | GET | Εργαστήρια ανά μάθημα |
| `/api/groups/<lab_id>` | GET | Τμήματα + occupancy |
| `/api/register-lab` | POST | Εγγραφή σε εργαστήριο |
| `/api/change-group` | PUT | Αλλαγή τμήματος |
| `/api/student/enrollments` | GET | Εγγραφές φοιτητή |
| `/api/student/profile` | GET/PUT | Προφίλ φοιτητή |
| `/api/student/notifications` | GET | Ειδοποιήσεις απουσιών |

## 🧪 Testing
Terminal 1: Start server

cd thesis/unilabs/app python app.py

Terminal 2: Run tests
python run_tests.py

## 📊 Database

Κύριοι πίνακες:
- `student` - Φοιτητές
- `professor` - Καθηγητές  
- `coursename` - Μαθήματα
- `course_lab` - Εργαστήρια
- `lab_groups` - Τμήματα
- `rel_lab_student` - Εγγραφές σε εργαστήρια
- `rel_group_student` - Εγγραφές σε τμήματα
- `student_misses_pergroup` - Απουσίες

## 🔒 Production Deployment

1. Set `AUTH_MODE=cas`
2. Configure CAS URLs in `app.py`: CAS_SERVER_URL = 'https://sso.uoi.gr/login' CAS_SERVICE_URL = 'https://your-domain.gr/cas_callback'
3. Set secure `SECRET_KEY`
4. Use production WSGI (gunicorn/uwsgi)

## 📚 Documentation

- [Dev Mode Guide](tests/DEV_MODE_GUIDE.md)
- [Authorization Guide](tests/AUTHORIZATION_GUIDE.md)
- [Testing Checklist](app/TESTING_CHECKLIST.md)

## 🔄 Migration από LabRegFrontCas

Αυτό το project αντικαθιστά το παλιό `LabRegFrontCas` με:
- Νέο Flask backend (Python)
- Modern Bootstrap 5 UI
- REST APIs
- Role-based authorization

---
## GitHub Repository
[https://github.com/nikosmakas/unilabs]
