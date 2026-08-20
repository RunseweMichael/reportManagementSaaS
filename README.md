# TutorOS — Django Tutor Management Platform

A full-featured tutor management system built with Django (no React/API). 
Supports online and physical tutors, student tracking, attendance, timetables, and weekly reports.

## Features

### Tutor Portal
- **Dashboard** — weekly class overview, student summary, attendance rate, report status
- **Classes** — create/edit/delete sessions; view per-class attendance
- **Attendance** — take attendance per class with Present/Absent + optional notes
- **Timetable** — weekly schedule with conflict detection
- **Students** — view assigned students, progress, attendance history
- **Weekly Reports** — submit weekly summaries; see admin feedback

### Admin Panel
- **Dashboard** — platform-wide stats split by Online vs Physical
- **Tutors** — full CRUD; filter by Online/Physical; view per-tutor detail
- **Students** — full CRUD; filter by mode or tutor
- **Timetable** — combined view of all tutors; colour-coded by mode
- **Reports** — review submitted reports; add feedback; mark as reviewed
- **Courses** — manage courses and curriculum

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run migrations
```bash
python manage.py migrate
```

### 3. Seed sample data (optional but recommended)
```bash
python manage.py seed_data
```

### 4. Run the server
```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/**

## Login Credentials (after seed_data)

| Role  | Username      | Password  | Redirect                    |
|-------|---------------|-----------|----------------------------- |
| Admin | `admin`       | `admin123`| `/admin-panel/dashboard/`   |
| Tutor | `ada_tutor`   | `tutor123`| `/tutor/dashboard/`         |
| Tutor | `emeka_tutor` | `tutor123`| `/tutor/dashboard/`         |
| Tutor | `ngozi_tutor` | `tutor123`| `/tutor/dashboard/`         |
| Tutor | `bode_tutor`  | `tutor123`| `/tutor/dashboard/`         |

## URL Structure

| Path                         | Description                   |
|------------------------------|-------------------------------|
| `/`                          | Login page                    |
| `/tutor/dashboard/`          | Tutor dashboard               |
| `/tutor/classes/`            | Tutor's class list            |
| `/tutor/classes/<id>/`       | Class detail + attendance     |
| `/tutor/timetable/`          | Tutor weekly timetable        |
| `/tutor/students/`           | Tutor's student list          |
| `/tutor/reports/`            | Tutor weekly reports          |
| `/admin-panel/dashboard/`    | Admin overview                |
| `/admin-panel/tutors/`       | All tutors (filterable)       |
| `/admin-panel/students/`     | All students (filterable)     |
| `/admin-panel/timetable/`    | Combined timetable            |
| `/admin-panel/reports/`      | All reports (review workflow) |
| `/admin-panel/courses/`      | Course management             |
| `/django-admin/`             | Django built-in admin         |

## Models

- **Course** — name, code, duration
- **Topic** — course topics by week/day
- **Tutor** — name, email, mode (online/physical), linked to User
- **Student** — name, mode, assigned tutor, courses
- **Class** — a session with course/tutor/topic/date/students
- **Attendance** — per-student per-class record (Present/Absent)
- **TimetableEntry** — recurring schedule with overlap validation
- **WeeklyReport** — tutor's weekly summary with admin feedback workflow

## Production Notes

- Change `SECRET_KEY` in settings.py (use environment variables)
- Set `DEBUG=False`
- Configure a proper database (PostgreSQL recommended)
- Set up `ALLOWED_HOSTS`
- Run `python manage.py collectstatic`
