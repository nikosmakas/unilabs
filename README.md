# UniLabs - Σύστημα Διαχείρισης Εργαστηρίων

Διαδικτυακή εφαρμογή για τη διαχείριση εργαστηρίων και εγγραφών φοιτητών.

## 📁 Δομή Project
```
thesis/unilabs/
├── app/                            # Flask Application Root
│   ├── data/
│   │   ├── labregister.sqlite      # SQLite Database
│   │   └── data_labregister.sql    # Schema Backup & Initial Data
│   ├── routes/
│   │   ├── api.py                  # REST API Endpoints
│   │   ├── auth_routes.py          # Authentication (CAS + Dev Mode)
│   │   └── views.py               # Page Routes (Blueprints)
│   ├── static/css/style.css        # Stylesheet (Dark/Light theme)
│   ├── templates/                  # Jinja2 HTML Templates
│   ├── app.py                      # Main Entry Point
│   ├── auth.py                     # Authorization & Registration Logic
│   ├── helpers.py                  # Utility Functions
│   ├── models.py                   # SQLAlchemy Database Models
│   ├── requirements.txt            # Python Dependencies
│   └── run_tests.py                # Automated Testing Suite
│
├── docs/
│   ├── AUTHORIZATION_GUIDE.md      # Detailed Authorization Docs
│   ├── DEV_MODE_GUIDE.md           # Documentation for Developer Mode
│   ├── TESTING_CHECKLIST.md        # Manual Testing & QA Guide
│   └── previous_project_blueprint.json
│
├── tests/
│   └── test_dev_auth.py            # Authentication & Security Tests
│
├── seed.py                         # Database Seeder (mock data)
├── .gitignore
└── README.md
```

## 🚀 Γρήγορη Εκκίνηση

### 1. Εγκατάσταση
```bash
cd thesis/unilabs/app
pip install -r requirements.txt
```

### 2. Seed Database (mock data)
```bash
cd thesis/unilabs
python seed.py
```

### 3. Εκκίνηση Server
```bash
cd thesis/unilabs/app
python app.py
```

### 4. Πρόσβαση
Άνοιξε: **http://localhost:5000/login**

## 🔐 Development Mode

Για testing χωρίς CAS authentication:

| User       | Role         | ID      | Description              |
|------------|--------------|---------|--------------------------|
| `student1` | Φοιτητής     | AM 13628| Dev test student         |
| `student2` | Φοιτητής     | AM 10001| Αλεξίου Μαρία            |
| `prof1`    | Καθηγητής    | ID 101  | Παπαδόπουλος Νίκος       |
| `prof2`    | Καθηγήτρια   | ID 102  | Αντωνίου Ελένη           |
| `admin1`   | Διαχειριστής | ID 999  | Full access              |

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
| `/api/student/enrollment/<lab_id>` | DELETE | Απεγγραφή από εργαστήριο |
| `/api/student/enrollments` | GET | Εγγραφές φοιτητή |
| `/api/student/profile` | GET/PUT | Προφίλ φοιτητή |
| `/api/student/notifications` | GET | Ειδοποιήσεις απουσιών |
| `/api/professor/my-groups` | GET | Τμήματα καθηγητή |
| `/api/professor/group/<id>/students` | GET | Φοιτητές τμήματος |
| `/api/professor/profile` | PUT | Επεξεργασία προφίλ καθηγητή |
| `/api/labs/<lab_id>/description` | PUT | Επεξεργασία περιγραφής εργαστηρίου |

## 🧪 Testing
```bash
# Terminal 1: Seed + start server
cd thesis/unilabs
python seed.py
cd app
python app.py

# Terminal 2: Run tests
cd thesis/unilabs/app
python run_tests.py
```

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

- [Dev Mode Guide](docs/DEV_MODE_GUIDE.md)
- [Authorization Guide](docs/AUTHORIZATION_GUIDE.md)
- [Testing Checklist](docs/TESTING_CHECKLIST.md)

## 🔄 Migration από LabRegFrontCas

Αυτό το project αντικαθιστά το παλιό `LabRegFrontCas` με:
- Νέο Flask backend (Python)
- Modern Bootstrap 5 UI
- REST APIs
- Role-based authorization

---
## GitHub Repository
[https://github.com/nikosmakas/unilabs]
