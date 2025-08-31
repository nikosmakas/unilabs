# UniLabs

Μελέτη, σχεδίαση και υλοποίηση διαδικτυακής εφαρμογής για τη διαχείριση εργαστηρίων και εγγραφών φοιτητών.

## Δομή Project

thesis/ # Root folder
├── .venv/ # Python virtual environment
├── unilabs/ # Flask application
│ ├── app.py # Κύριο Flask app (routes)
│ ├── models.py # Ορισμοί πινάκων βάσης (SQLAlchemy)
│ ├── data/ # Αρχεία βάσης δεδομένων
│ │ ├── data_labregister.sql
│ │ └── labregister.sqlite
│ ├── templates/ # Jinja2 templates
│ │ ├── dashboard.html
│ │ └── login.html
│ ├── requirements.txt # Εξαρτήσεις Python
│ └── sqlite3.exe # SQLite binary (για local testing)



## Οδηγίες Εκκίνησης

1. **Εγκατάσταση εξαρτήσεων**
   ```bash
   pip install -r requirements.txt
   ```
2. **Αρχικοποίηση βάσης (προαιρετικά)**
   - Τρέξε το Flask app και επισκέψου το `/init-db` για να δημιουργηθούν τα tables και να εισαχθούν τα δεδομένα.
3. **Ρύθμιση CAS** - Χρησιμοποίησε AM και password από τα demo δεδομένα (π.χ. 12345/12345).
	Επεξεργαστείτε το app.py και ορίστε
	CAS_SERVER_URL = 'https://sso.uoi.gr/login'
    CAS_SERVICE_URL = 'http://localhost:5000/cas_callback'  # Προσαρμογή ανάλογα με το environment
4. **Εκκίνηση εφαρμογής**
   ```bash
   cd unilabs\app
   python app.py
   ```
5. **Πρόσβαση στην εφαρμογή**
   - Ανοίξτε τον περιηγητή σας και επισκεφθείτε `http://localhost:5000/login` για να συνδεθείτε μέσω CAS. 


## Διάγραμμα Ροής Εφαρμογής
   (mermaid diagram)
```
sequenceDiagram
    User->>+Flask: GET /login
    Flask->>+CAS: Redirect to CAS login
    CAS->>+User: Σύνδεση με πανεπιστημιακά credentials
    User->>+Flask: GET /cas_callback?ticket=XYZ
    Flask->>+CAS: Επαλήθευση ticket
    CAS->>+Flask: Attributes (schGrAcPersonID, eduPersonAffiliation)
    Flask->>+Database: Έλεγχος ύπαρξης χρήστη
    alt Χρήστης υπάρχει
        Flask->>+User: Redirect /dashboard
    else Χρήστης δεν υπάρχει
        Flask->>+User: Error "Δεν έχετε πρόσβαση"
    end
```
## Περιγραφή
-Routes: Όλες οι διαδρομές βρίσκονται στο app.py
-Models: Ορισμοί πινάκων βάσης στο models.py (SQLAlchemy)
-Templates:
    login.html: Σελίδα σύνδεσης με CAS
    dashboard.html: Κύρια σελίδα εφαρμογής (διαφορετική για καθηγητές/φοιτητές)
-Δεδομένα:
    data_labregister.sql: SQL dump αρχικής βάσης
    labregister.sqlite: SQLite database file

## GitHub Repository
[https://github.com/nikosmakas/thesis]
