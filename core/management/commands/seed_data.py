from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import date, timedelta, time
from core.models import (
    Course, Topic, Tutor, Student, Class,
    Attendance, TimetableEntry, WeeklyReport, Classroom
)


class Command(BaseCommand):
    help = 'Seeds the database with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # ── Superuser ─────────────────────────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@tutoros.com', 'admin123')
            self.stdout.write('  Created superuser: admin / admin123')

        # ── Courses ───────────────────────────────────────────────────────────
        py_course, _ = Course.objects.get_or_create(
            code='PY101',
            defaults={'name': 'Python Programming', 'description': 'Intro to Python', 'duration_weeks': 12}
        )
        web_course, _ = Course.objects.get_or_create(
            code='WD201',
            defaults={'name': 'Web Development', 'description': 'HTML/CSS/JS & Django', 'duration_weeks': 16}
        )
        ds_course, _ = Course.objects.get_or_create(
            code='DS301',
            defaults={'name': 'Data Science', 'description': 'ML and analytics', 'duration_weeks': 10}
        )

        # ── Topics ────────────────────────────────────────────────────────────
        py_topics_data = [
            (1, 1, 'Variables & Data Types', 'Integers, strings, floats, booleans'),
            (1, 2, 'Control Flow',           'if/else, loops'),
            (2, 1, 'Functions',              'def, return, scope'),
            (2, 2, 'Lists & Dictionaries',   'Core data structures'),
            (3, 1, 'OOP Basics',             'Classes and objects'),
            (3, 2, 'File Handling',          'Reading and writing files'),
        ]
        py_topics = []
        for week, day, title, details in py_topics_data:
            t, _ = Topic.objects.get_or_create(
                course=py_course, week=week, day=day,
                defaults={'title': title, 'details': details}
            )
            py_topics.append(t)

        web_topics_data = [
            (1, 1, 'HTML Structure',    'Tags, elements, attributes'),
            (1, 2, 'CSS Styling',       'Selectors, box model'),
            (2, 1, 'JavaScript Basics', 'Variables, functions, DOM'),
            (2, 2, 'Responsive Design', 'Flexbox, Grid, media queries'),
        ]
        web_topics = []
        for week, day, title, details in web_topics_data:
            t, _ = Topic.objects.get_or_create(
                course=web_course, week=week, day=day,
                defaults={'title': title, 'details': details}
            )
            web_topics.append(t)

        # ── Tutors + user accounts ─────────────────────────────────────────
        tutors_raw = [
            ('Ada Okafor',   'ada@tutoros.com',   'online',   'Python & Data Science', 'ada_tutor'),
            ('Emeka Chukwu', 'emeka@tutoros.com', 'physical', 'Web Development',       'emeka_tutor'),
            ('Ngozi Ibe',    'ngozi@tutoros.com', 'online',   'Data Science',          'ngozi_tutor'),
            ('Bode Adeyemi', 'bode@tutoros.com',  'physical', 'Python & Django',       'bode_tutor'),
        ]
        tutor_objs = []
        for name, email, mode, spec, uname in tutors_raw:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(
                    uname, email, 'tutor123',
                    first_name=name.split()[0], last_name=name.split()[1]
                )
            else:
                u = User.objects.get(username=uname)
            t, _ = Tutor.objects.get_or_create(
                email=email,
                defaults={'name': name, 'mode': mode, 'specialization': spec, 'active': True}
            )
            if not t.user:
                t.user = u
                t.save()
            tutor_objs.append(t)

        ada, emeka, ngozi, bode = tutor_objs

        # ── Classrooms (create BEFORE students) ───────────────────────────
        today = date.today()

        cr_py_a, _ = Classroom.objects.get_or_create(
            name='Python Batch A — May 2026',
            defaults={
                'course':      py_course,
                'tutor':       ada,
                'status':      'active',
                'start_date':  today - timedelta(weeks=3),
                'end_date':    today + timedelta(weeks=9),
                'description': 'Online Python cohort. Classes Mon & Wed.',
            }
        )
        cr_py_b, _ = Classroom.objects.get_or_create(
            name='Python Batch B — June 2026',
            defaults={
                'course':      py_course,
                'tutor':       ada,
                'status':      'active',
                'start_date':  today - timedelta(days=3),
                'end_date':    today + timedelta(weeks=11),
                'description': 'New Python cohort.',
            }
        )
        cr_web, _ = Classroom.objects.get_or_create(
            name='Web Dev Cohort — May 2026',
            defaults={
                'course':      web_course,
                'tutor':       emeka,
                'status':      'active',
                'start_date':  today - timedelta(weeks=2),
                'end_date':    today + timedelta(weeks=14),
                'description': 'Physical classroom, Tue & Thu.',
            }
        )
        cr_py_phys, _ = Classroom.objects.get_or_create(
            name='Python Physical — April 2026',
            defaults={
                'course':      py_course,
                'tutor':       bode,
                'status':      'active',
                'start_date':  today - timedelta(weeks=5),
                'end_date':    today + timedelta(weeks=7),
                'description': 'In-person Python class.',
            }
        )

        # ── Students (no user accounts needed) ────────────────────────────
        students_raw = [
            ('Chisom Nweze',  'chisom@example.com',  'online',   ada,   cr_py_a),
            ('Tunde Bakare',  'tunde@example.com',   'online',   ada,   cr_py_b),
            ('Amaka Obi',     'amaka@example.com',   'online',   ngozi, cr_py_b),
            ('Segun Alabi',   'segun@example.com',   'physical', emeka, cr_web),
            ('Funmi Adewale', 'funmi@example.com',   'physical', emeka, cr_web),
            ('Kola Peters',   'kola@example.com',    'physical', bode,  cr_py_phys),
            ('Yetunde Ojo',   'yetunde@example.com', 'online',   ada,   cr_py_a),
            ('Ibrahim Musa',  'ibrahim@example.com', 'physical', bode,  cr_py_phys),
        ]
        student_objs = []
        for name, email, mode, tutor, classroom in students_raw:
            s, created = Student.objects.get_or_create(
                email=email,
                defaults={
                    'name':  name,
                    'mode':  mode,
                    'tutor': tutor,
                    'active': True,
                    'current_week': 2,
                }
            )
            s.courses.add(classroom.course)
            classroom.students.add(s)
            student_objs.append(s)

        chisom, tunde, amaka, segun, funmi, kola, yetunde, ibrahim = student_objs

        # ── Timetable ─────────────────────────────────────────────────────
        timetable_raw = [
            (ada,   py_course,  0, time(9, 0),  time(11, 0), 'Python Morning'),
            (ada,   ds_course,  2, time(14, 0), time(16, 0), 'Data Science'),
            (emeka, web_course, 1, time(10, 0), time(12, 0), 'Web Dev'),
            (emeka, web_course, 3, time(10, 0), time(12, 0), 'Web Dev'),
            (ngozi, ds_course,  4, time(9, 0),  time(11, 0), 'DS Friday'),
            (bode,  py_course,  1, time(14, 0), time(16, 0), 'Python Afternoon'),
            (bode,  py_course,  4, time(14, 0), time(16, 0), 'Python Friday'),
        ]
        for tutor, course, day, start, end, subject in timetable_raw:
            TimetableEntry.objects.get_or_create(
                tutor=tutor, course=course, day_of_week=day,
                defaults={'start_time': start, 'end_time': end, 'subject': subject}
            )

        # ── Sessions inside classrooms ─────────────────────────────────
        session_records = []

        # Python Batch A — 3 sessions
        for weeks_back, topic in [(3, py_topics[0]), (2, py_topics[1]), (1, py_topics[2])]:
            cls, _ = Class.objects.get_or_create(
                tutor=ada, course=py_course,
                date=today - timedelta(weeks=weeks_back),
                classroom=cr_py_a,
                defaults={'topic': topic, 'start_time': time(9, 0), 'end_time': time(11, 0)}
            )
            cls.students.set(cr_py_a.students.all())
            session_records.append((cls, list(cr_py_a.students.all())))

        # Web Dev Cohort — 2 sessions
        for weeks_back, topic in [(2, web_topics[0]), (1, web_topics[1])]:
            cls, _ = Class.objects.get_or_create(
                tutor=emeka, course=web_course,
                date=today - timedelta(weeks=weeks_back),
                classroom=cr_web,
                defaults={'topic': topic, 'start_time': time(10, 0), 'end_time': time(12, 0)}
            )
            cls.students.set(cr_web.students.all())
            session_records.append((cls, list(cr_web.students.all())))

        # Python Physical — 2 sessions
        for weeks_back, topic in [(2, py_topics[0]), (1, py_topics[1])]:
            cls, _ = Class.objects.get_or_create(
                tutor=bode, course=py_course,
                date=today - timedelta(weeks=weeks_back),
                classroom=cr_py_phys,
                defaults={'topic': topic, 'start_time': time(14, 0), 'end_time': time(16, 0)}
            )
            cls.students.set(cr_py_phys.students.all())
            session_records.append((cls, list(cr_py_phys.students.all())))

        # ── Attendance ────────────────────────────────────────────────────
        pattern = ['Present', 'Present', 'Present', 'Absent', 'Present', 'Present', 'Present']
        for i, (cls, studs) in enumerate(session_records):
            for j, student in enumerate(studs):
                Attendance.objects.get_or_create(
                    student=student, class_instance=cls,
                    defaults={
                        'date':              cls.date,
                        'attendance_status': pattern[(i + j) % len(pattern)],
                    }
                )

        # ── Weekly reports ────────────────────────────────────────────────
        week_start = today - timedelta(days=today.weekday())
        last_start = week_start - timedelta(weeks=1)
        last_end   = last_start + timedelta(days=6)

        WeeklyReport.objects.get_or_create(
            tutor=ada, week_start=last_start,
            defaults={
                'week_end':          last_end,
                'classes_held':      2,
                'students_attended': 3,
                'topics_covered':    'Python variables, loops, control flow',
                'challenges':        'Some students struggled with list comprehensions',
                'plan_next_week':    'Cover functions and modules',
                'status':            'submitted',
            }
        )
        WeeklyReport.objects.get_or_create(
            tutor=emeka, week_start=last_start,
            defaults={
                'week_end':          last_end,
                'classes_held':      2,
                'students_attended': 2,
                'topics_covered':    'HTML structure, CSS basics',
                'challenges':        'Internet connectivity issues for one student',
                'plan_next_week':    'JavaScript introduction',
                'status':            'reviewed',
                'admin_feedback':    'Great work! Keep up the engagement.',
            }
        )

        self.stdout.write(self.style.SUCCESS('\nDone! Sample data created.'))
        self.stdout.write('\n--- Login Credentials ---')
        self.stdout.write('Admin:  admin        / admin123  → /admin-panel/dashboard/')
        self.stdout.write('Tutors: ada_tutor    / tutor123  → /tutor/dashboard/')
        self.stdout.write('        emeka_tutor  / tutor123')
        self.stdout.write('        ngozi_tutor  / tutor123')
        self.stdout.write('        bode_tutor   / tutor123')
        self.stdout.write('\nStudents have NO login — managed by tutors/admin only.')
