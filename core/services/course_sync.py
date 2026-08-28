# core/services/course_sync.py
import requests
from django.conf import settings
from django.utils.text import slugify
from core.models import Course, Module

COURSES_URL = getattr(settings, 'COURSES_API_URL',
    'https://studentmgt.whalesharkengineering.com.ng/api/courses/courses/')
MODULES_URL = getattr(settings, 'MODULES_API_URL',
    'https://studentmgt.whalesharkengineering.com.ng/api/courses/modules/')


def _headers():
    h = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
    }
    if getattr(settings, 'STUDENT_API_TOKEN', None):
        h['Authorization'] = f"Token {settings.STUDENT_API_TOKEN}"
    return h


def _paginated_get(url):
    rows = []
    while url:
        resp = requests.get(url, headers=_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        page = data.get('results', data) if isinstance(data, dict) else data
        rows.extend(page)
        url = data.get('next') if isinstance(data, dict) else None
    return rows


def sync_courses():
    created, updated = 0, 0
    for row in _paginated_get(COURSES_URL):
        ext_id = row['id']
        name = row.get('course_name') or row.get('name') or f"Course {ext_id}"

        defaults = {
            'name': name,
            'price': row.get('price'),
            'duration': row.get('duration'),
            'duration_weeks': row.get('duration') or 12,
            'skills': row.get('skills', '') or '',
            'resource_link': row.get('resource_link', '') or '',
            'is_synced': True,
        }

        # only set 'code' the first time a course is created — never overwrite on resync
        if not Course.objects.filter(external_id=ext_id).exists():
            base = slugify(name)[:15].upper() or f"CRS{ext_id}"
            defaults['code'] = f"{base}-{ext_id}"

        obj, was_created = Course.objects.update_or_create(
            external_id=ext_id, defaults=defaults
        )
        created += was_created
        updated += (not was_created)
    return created, updated


# core/services/course_sync.py — replace sync_modules with this corrected version
def sync_modules():
    created, updated = 0, 0
    for row in _paginated_get(MODULES_URL):
        ext_id = row['id']
        course_ext_id = row.get('course')  # plain int, not nested object
        course = Course.objects.filter(external_id=course_ext_id).first()
        if not course:
            continue  # its parent course hasn't synced yet — run sync_courses first

        defaults = {
            'course': course,
            'name': row.get('title') or f"Module {ext_id}",   # ← API field is 'title'
            'order': row.get('order', 1),
            'description': '',   # not present in payload — stays local-editable
        }
        obj, was_created = Module.objects.update_or_create(
            external_id=ext_id, defaults=defaults
        )
        created += was_created
        updated += (not was_created)
    return created, updated