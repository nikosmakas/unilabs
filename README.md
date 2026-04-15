# UniLabs - University Laboratory Management System

A full-featured web application for managing university laboratory registrations, student groups, grades, and absences. Built as a thesis project for the Department of Informatics & Telecommunications, University of Ioannina.

## Key Features

- **Role-Based Access Control (RBAC)** - Separate views and permissions for Students, Professors, and Administrators
- **Cascading Registration** - Students register via Semester > Course > Lab > Group dropdowns with real-time occupancy
- **Grades & Absences** - Professors record absences per date and assign grades (0-10) with auto-status updates
- **CSV Import/Export** - Bulk import eligibility lists; export group rosters as UTF-8 BOM CSV (Excel-compatible)
- **Admin Dashboard** - Full CRUD for Labs, Groups, Courses, and Professors with safety checks
- **Internationalization (i18n)** - Greek/English UI switching via Flask-Babel
- **CAS SSO Ready** - Pluggable authentication supporting both CAS single sign-on and local dev mode
- **Dark/Light Theme** - User-selectable theme with localStorage persistence
- **Responsive Design** - Collapsible sidebar, mobile-first layout with Bootstrap 5

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3.11+, Flask 2.3+           |
| Database    | SQLite (via Flask-SQLAlchemy)       |
| Frontend    | Bootstrap 5.3, Font Awesome 6      |
| i18n        | Flask-Babel 4.0                     |
| Auth        | CAS SSO / Dev mode (Flask-Login)   |

## Project Structure

```
unilabs/
├── app/
│   ├── app.py              # Flask application factory & config
│   ├── auth.py             # Authentication, RBAC, enrollment logic
│   ├── helpers.py          # Shared utility functions
│   ├── models.py           # SQLAlchemy ORM models
│   ├── routes/
│   │   ├── api.py          # REST API endpoints
│   │   ├── auth_routes.py  # Login/logout routes
│   │   └── views.py        # Page rendering routes
│   ├── templates/          # Jinja2 HTML templates
│   ├── static/             # CSS, JS assets
│   ├── data/               # SQLite database file
│   └── translations/       # i18n message catalogs (en, el)
├── babel.cfg               # Babel extraction config
├── compile_translations.py # Compile .po to .mo (no CLI needed)
├── requirements.txt        # Python dependencies
└── README.md
```

## Installation

### 1. Clone & Install Dependencies

```bash
cd unilabs
pip install -r requirements.txt
```

### 2. Seed the Database (Development)

```bash
python seed.py
```

### 3. Compile Translations

```bash
python compile_translations.py
```

### 4. Start the Server

```bash
cd app
python app.py
```

Open **http://localhost:5000/login** in your browser.

## Development Mode

Set `AUTH_MODE=dev` in your environment (or `.env` file) to enable local authentication without CAS.

| Username   | Role          | ID       | Description              |
|------------|---------------|----------|--------------------------|
| `student1` | Student       | AM 13628 | Dev test student         |
| `student2` | Student       | AM 10001 | Dev test student 2       |
| `prof1`    | Professor     | ID 101   | Test professor           |
| `prof2`    | Professor     | ID 102   | Test professor 2         |
| `admin1`   | Administrator | ID 999   | Full admin access        |

## API Reference

### Public (Authenticated)

| Endpoint                             | Method | Description                    |
|--------------------------------------|--------|--------------------------------|
| `/api/semesters`                     | GET    | List semesters                 |
| `/api/courses/<semester>`            | GET    | Courses by semester            |
| `/api/labs/<course_id>`              | GET    | Labs by course                 |
| `/api/groups/<lab_id>`               | GET    | Groups with occupancy          |
| `/api/register-lab`                  | POST   | Register for a lab group       |
| `/api/change-group`                  | PUT    | Change enrolled group          |
| `/api/student/enrollment/<lab_id>`   | DELETE | Unenroll from a lab            |
| `/api/student/enrollments`           | GET    | Current student enrollments    |
| `/api/student/notifications`         | GET    | Absence notifications          |

### Professor / Admin

| Endpoint                                          | Method | Description                |
|---------------------------------------------------|--------|----------------------------|
| `/api/professor/my-groups`                        | GET    | Professor's assigned groups|
| `/api/professor/group/<id>/students`              | GET    | Group student roster       |
| `/api/professor/group/<id>/student/<am>/grade`    | PUT    | Update student grade       |
| `/api/professor/group/<id>/student/<am>/absence`  | POST   | Record absence             |
| `/api/professor/group/<id>/student/<am>/absence`  | DELETE | Remove absence             |
| `/api/professor/group/<id>/export`                | GET    | Export group CSV           |

### Admin Only

| Endpoint                                     | Method | Description                |
|----------------------------------------------|--------|----------------------------|
| `/api/admin/labs`                            | POST   | Create lab                 |
| `/api/admin/labs/<id>`                       | PUT    | Edit lab                   |
| `/api/admin/labs/<id>`                       | DELETE | Delete lab                 |
| `/api/admin/groups`                          | POST   | Create group               |
| `/api/admin/groups/<id>`                     | PUT    | Edit group                 |
| `/api/admin/groups/<id>`                     | DELETE | Delete group               |
| `/api/admin/courses`                         | POST   | Create course              |
| `/api/admin/courses/<id>`                    | DELETE | Delete course              |
| `/api/admin/professors`                      | POST   | Create professor           |
| `/api/admin/professors/<id>`                 | DELETE | Delete professor           |
| `/api/admin/course/<id>/import-eligible`     | POST   | Import eligibility CSV     |
| `/api/admin/course/<id>/clear-eligible`      | DELETE | Clear eligibility list     |

## Adding Translations

1. Add `_('New Greek Text')` calls in Jinja templates
2. Add corresponding entries to `app/translations/en/LC_MESSAGES/messages.po`
3. Run `python compile_translations.py` from the `unilabs/` directory

## License

This project was developed as a thesis for the University of Ioannina.
