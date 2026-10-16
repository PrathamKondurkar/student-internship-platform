# Student Skill & Internship Platform

A full-stack academic project built with HTML, CSS, JavaScript, Python (Flask), MongoDB, SQLite for relational reporting, and GitHub Actions CI.

## Features
- Student, company, and admin roles
- Registration/login with password hashing and session-based authentication
- Student profile and skill management
- Companies can post internships and review applications
- Students can apply once per internship and track application status
- Explainable skill-match recommendations
- MongoDB aggregation analytics
- SQLite relational reporting example to demonstrate SQL + NoSQL integration
- Input validation, role checks, error handling, tests, and CI workflow

## Tech stack
- Frontend: HTML, CSS, vanilla JavaScript
- Backend: Python + Flask REST API
- Main database: MongoDB
- Relational reporting database: SQLite
- ML: skill overlap scoring (a transparent baseline recommendation model)
- Version control / pipeline: Git + GitHub Actions

## Requirements
- Python 3.10+
- MongoDB Community Server running locally, or a MongoDB Atlas URI
- Git (optional, for version control)

## Run locally (Windows PowerShell)
1. Extract the ZIP and open a terminal in the project folder.
2. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and set `MONGO_URI` if needed.
   ```powershell
   Copy-Item .env.example .env
   ```
5. Start MongoDB locally, then run:
   ```powershell
   python run.py
   ```
6. Open http://127.0.0.1:5000

## Run locally (macOS/Linux)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

## Demo accounts
For safety, the app does not create hard-coded demo passwords. Register through the UI:
- Student: choose role `student`
- Company: choose role `company`
- Admin: set `ALLOW_ADMIN_REGISTRATION=true` in `.env` temporarily, register an admin, then turn it off.

The app requires MongoDB for normal operation. SQLite reporting tables are initialized automatically.

## API overview
- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/me`
- `GET|PUT /api/student/profile`
- `GET|POST /api/internships`
- `GET|PUT|DELETE /api/internships/<id>`
- `POST /api/internships/<id>/apply`
- `GET /api/applications/mine`
- `GET /api/company/applications`
- `PATCH /api/applications/<id>/status`
- `GET /api/recommendations`
- `GET /api/analytics`

## SQL + NoSQL note
MongoDB stores the operational application data. SQLite stores a small relational reporting mirror for users, internships, and applications. The project includes a report query with joins/grouping in SQLite and MongoDB aggregation pipelines. This is a teaching/demo integration, not a distributed transaction system.

## Tests
```bash
pytest
```
Most tests exercise pure business logic and API validation without requiring a live MongoDB server. For integration testing, set `MONGO_URI` to a test MongoDB instance.

## Git workflow
```bash
git init
git add .
git commit -m "Initial student internship platform"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/student-internship-platform.git
git push -u origin main
```
Use feature branches and pull requests. GitHub Actions runs linting and tests on pushes and pull requests to `main`.

## Security and limitations
- Change `SECRET_KEY` before deployment.
- Use HTTPS and secure cookie settings in production.
- Set `ALLOW_ADMIN_REGISTRATION=false` except during controlled setup.
- This is an academic starter project; add CSRF protection, email verification, rate limiting, audit logging, and production deployment configuration before public launch.
