# core/management/commands/sync_courses.py
from django.core.management.base import BaseCommand
from core.services.course_sync import sync_courses, sync_modules

class Command(BaseCommand):
    help = "Pull courses and modules from the external student-management API"

    def handle(self, *args, **options):
        cc, cu = sync_courses()
        self.stdout.write(self.style.SUCCESS(f"Courses: {cc} created, {cu} updated."))
        mc, mu = sync_modules()
        self.stdout.write(self.style.SUCCESS(f"Modules: {mc} created, {mu} updated."))