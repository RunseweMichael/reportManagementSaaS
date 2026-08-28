# core/management/commands/sync_students.py
from django.core.management.base import BaseCommand
from core.services.student_sync import sync_students

class Command(BaseCommand):
    help = "Pull students from the external student-management API"

    def handle(self, *args, **options):
        created, updated = sync_students()
        self.stdout.write(self.style.SUCCESS(
            f"Sync complete — {created} created, {updated} updated."
        ))