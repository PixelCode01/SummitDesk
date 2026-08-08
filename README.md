# SummitDesk

A trek booking and management portal built with Flask. Three roles - admin, staff, and trekker - each with their own dashboard and workflow.

## What it does

- Admin creates treks, manages staff approvals, controls trek status lifecycle and monitors bookings
- Staff handle assigned treks, update slot counts and mark completion
- Trekkers browse open treks, book slots, join waitlists, cancel bookings and leave reviews
- Waitlist auto-promotes the next person when someone cancels
- REST API endpoints for treks, bookings and users
- Login rate limiting and role-based access control throughout

## Stack

- Flask with blueprints
- SQLAlchemy + SQLite
- Flask-Login for sessions
- Werkzeug for password hashing
- Jinja2 templates

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python seed.py
python run.py
```

App runs at `http://localhost:5000`

## Default accounts

| Role  | Username | Password |
|-------|----------|----------|
| Admin | admin    | admin123 |
| Staff | staff    | staff123 |

Register as a trekker from the login page. Staff accounts need admin approval before they can log in.

## Project structure

```
blueprints/
  admin.py   - trek and user management
  staff.py   - assigned trek operations
  user.py    - booking, waitlist, review flows
  auth.py    - login, register, logout
  api.py     - REST endpoints
models.py    - User, Trek, Booking, Review, Waitlist
decorators.py - role guards
seed.py      - seeds db with admin, staff and sample treks
```

## API

Base path `/api`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | /treks   | list all treks |
| POST   | /treks   | create trek |
| GET    | /treks/:id | get one trek |
| PUT    | /treks/:id | update trek |
| DELETE | /treks/:id | delete trek |
| GET    | /bookings | list bookings |
| GET    | /bookings/:id | booking detail |
| GET    | /users | list trekkers |
