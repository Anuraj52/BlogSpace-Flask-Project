# BlogSpace — Blogging Platform with Flask

A learning project covering authentication, post CRUD, categories, comments, search, pagination, profiles, tests and deployment configuration.

## Features
- User registration, login, logout and session management with Flask-Login
- Password hashing and protected routes
- Create, read, update and delete blog posts
- Categories linked to posts through SQLAlchemy models
- Authenticated comments
- Search by title or content and category filtering
- Paginated home page and user profile pages
- CSRF-protected Flask-WTF forms
- Unit tests with pytest
- Gunicorn and Render deployment configuration

## Run on Windows (VS Code)

Open the folder containing `app.py` in VS Code Terminal and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```

If PowerShell blocks activation, run this in the same terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Open http://127.0.0.1:5000

## Run tests

```powershell
pytest -q
```

## Before deployment
Set a strong random `SECRET_KEY` environment variable. Configure a persistent production database (SQLite is suitable for local demonstration; PostgreSQL is recommended for hosted production). Do not use the development server or `debug=True` in production.

## Main project structure

```text
BlogSpace_Flask_Project/
├── app.py
├── requirements.txt
├── Procfile
├── render.yaml
├── README.md
├── instance/             # database is created here on first run
├── static/css/style.css
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── post_form.html
│   ├── post_detail.html
│   ├── profile.html
│   └── error.html
└── tests/test_app.py
```

This is a starter implementation for learning and should be reviewed and tested before handling real user information.
