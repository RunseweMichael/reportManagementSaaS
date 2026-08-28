# core/services/student_sync.py
import requests
from django.conf import settings
from core.models import Student, Course
from django.utils import timezone

API_URL = getattr(
    settings, 'STUDENT_API_URL',
    'https://studentmgt.whalesharkengineering.com.ng/api/students/users/'
)

def sync_students():
    created, updated = 0, 0
    url = API_URL
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }
    if getattr(settings, 'STUDENT_API_TOKEN', None):
        headers['Authorization'] = f"Token {settings.STUDENT_API_TOKEN}"

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        print("STATUS:", resp.status_code)
        print("BODY:", resp.text[:1000])
        resp.raise_for_status()
        data = resp.json()
        rows = data.get('results', data) if isinstance(data, dict) else data

        for row in rows:
            course_obj = row.get('course') or {}
            defaults = {
                'name': row.get('name') or row.get('username') or '',
                'email': row.get('email') or '',
                'phone': row.get('phone_number') or '',
                'source_course_name': row.get('course_name') or course_obj.get('course_name', ''),
                'center': row.get('center') or '',
                'amount_paid': row.get('amount_paid'),
                'amount_owed': row.get('amount_owed'),
                'next_due_date': row.get('next_due_date') or None,
                'active': row.get('is_active', True),
                'mode': 'online' if (row.get('center') == 'Online') else 'physical',
                'is_synced': True,
            }

            defaults['last_synced_at'] = timezone.now()

            # NOTE: 'tutor' is deliberately excluded from defaults, so a
            # resync never overwrites an admin's assignment.
            obj, was_created = Student.objects.update_or_create(
                external_id=row['id'], defaults=defaults
            )
            created += was_created
            updated += (not was_created)

            # core/services/student_sync.py — inside the loop, after update_or_create
            course_ext_id = course_obj.get('id')
            if course_ext_id:
                course = Course.objects.filter(external_id=course_ext_id).first()
                if course:
                    obj.courses.add(course)

        url = data.get('next') if isinstance(data, dict) else None

    return created, updated