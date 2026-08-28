from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, date as date_type, timedelta


# core/models.py
class Course(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=20, unique=True)
    duration_weeks = models.PositiveIntegerField(default=12)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── new: sync fields ──
    external_id   = models.PositiveIntegerField(unique=True, null=True, blank=True, db_index=True)
    price         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    duration      = models.PositiveIntegerField(null=True, blank=True)  # raw value from API
    skills        = models.CharField(max_length=500, blank=True)
    resource_link = models.URLField(max_length=500, blank=True)
    is_synced     = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Module(models.Model):
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    name        = models.CharField(max_length=255)
    order       = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)

    # ── new ──
    external_id = models.PositiveIntegerField(unique=True, null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.name} — {self.name}"


class Topic(models.Model):
    course  = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="topics")
    module  = models.ForeignKey(          # ← new
        'Module', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='topics'
    )
    week    = models.PositiveIntegerField(default=1)
    day     = models.PositiveIntegerField(default=1)
    title   = models.CharField(max_length=200)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['module__order', 'week', 'day']

    def __str__(self):
        module_str = f"{self.module.name} — " if self.module else ""
        return f"{self.course.name} › {module_str}Wk{self.week} D{self.day}: {self.title}"


class Tutor(models.Model):
    MODE_CHOICES = [('online', 'Online'), ('physical', 'Physical')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='physical')
    active = models.BooleanField(default=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.get_mode_display()})"

    def get_this_week_classes(self):
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return self.classes.filter(date__range=[week_start, week_end])

    @property
    def name(self):
        if self.user:
            full = self.user.get_full_name()
            return full if full.strip() else self.user.username
        return f"Tutor #{self.pk}"

    @property
    def email(self):
        return self.user.email if self.user else ''


# core/models.py
class Student(models.Model):
    MODE_CHOICES = [('online', 'Online'), ('physical', 'Physical')]

    # ── existing fields stay exactly as they are ──
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    courses = models.ManyToManyField(Course, related_name="students", blank=True)
    tutor = models.ForeignKey(Tutor, on_delete=models.SET_NULL, null=True, blank=True, related_name="students")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='physical')
    active = models.BooleanField(default=True)
    current_week = models.PositiveIntegerField(default=1)
    enrolled_at = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    # ── new: sync bookkeeping (all nullable/blank so no existing row breaks) ──
    external_id = models.PositiveIntegerField(unique=True, null=True, blank=True, db_index=True)
    source_course_name = models.CharField(max_length=255, blank=True)
    center = models.CharField(max_length=50, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    amount_owed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    is_synced = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def attendance_rate(self):
        total = self.attendance_set.count()
        if total == 0:
            return 0
        present = self.attendance_set.filter(attendance_status='Present').count()
        return round((present / total) * 100)


class TimetableEntry(models.Model):
    LOCATION_CHOICES = [
        ('online',  'Online'),
        ('orogun',  'Orogun'),
        ('samonda', 'Samonda'),
    ]
    DAYS = [(0,'Monday'),(1,'Tuesday'),(2,'Wednesday'),(3,'Thursday'),(4,'Friday'),(5,'Saturday'),(6,'Sunday')]
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='timetable')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    day_of_week = models.IntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    students = models.ManyToManyField(Student, related_name='timetable_entries', blank=True)
    
    location = models.CharField(
        max_length=20,
        choices=LOCATION_CHOICES,
        blank=True, default='',
        help_text="Physical location (for in-person sessions only)."
    )

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('Start time must be before end time.')
        if self.tutor_id:
            overlapping = TimetableEntry.objects.filter(
                tutor=self.tutor, day_of_week=self.day_of_week
            ).exclude(pk=self.pk).filter(
                start_time__lt=self.end_time, end_time__gt=self.start_time,
            )
            if overlapping.exists():
                raise ValidationError('This overlaps with an existing timetable entry.')

    def __str__(self):
        return f"{self.tutor.name} – {self.get_day_of_week_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def duration_minutes(self):
        start = datetime.combine(date_type.today(), self.start_time)
        end = datetime.combine(date_type.today(), self.end_time)
        return int((end - start).total_seconds() / 60)


class Classroom(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
    ]
    name        = models.CharField(max_length=255)
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='classrooms')
    tutor       = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='classrooms')
    students    = models.ManyToManyField(Student, related_name='classrooms', blank=True)
    join_code   = models.CharField(max_length=8, unique=True, editable=False)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date  = models.DateField()
    end_date    = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.join_code = get_random_string(8).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.course.name})"

    @property
    def current_week(self):
        if self.start_date:
            delta = (date_type.today() - self.start_date).days
            return max(1, (delta // 7) + 1)
        return 1
    
    @property
    def progress_percent(self):
        if not self.end_date or not self.start_date:
            return 0
        total   = (self.end_date - self.start_date).days
        elapsed = (date_type.today() - self.start_date).days
        return min(100, round((elapsed / total) * 100)) if total > 0 else 0

    @property
    def attendance_rate(self):
        sessions = self.sessions.all()
        total    = Attendance.objects.filter(class_instance__in=sessions).count()
        present  = Attendance.objects.filter(
            class_instance__in=sessions, attendance_status='Present'
        ).count()
        return round((present / total) * 100) if total else 0


class Class(models.Model):
    course       = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="classes")
    tutor        = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name="classes")
    classroom    = models.ForeignKey(Classroom, on_delete=models.SET_NULL, null=True, blank=True, related_name="sessions")
    topic        = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="classes")  # kept as "primary topic" for old reads
    topics       = models.ManyToManyField(Topic, blank=True, related_name="sessions_multi")   # ← new: multi-select
    manual_topic = models.CharField(max_length=255, blank=True)                               # ← new: free-text fallback
    date         = models.DateField()
    start_time   = models.TimeField(null=True, blank=True)
    end_time     = models.TimeField(null=True, blank=True)
    description  = models.TextField(blank=True)
    comment      = models.TextField(blank=True)
    code         = models.CharField(max_length=10, unique=True, editable=False, blank=True)
    students     = models.ManyToManyField(Student, related_name="classes", blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Classes"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = get_random_string(6).upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.name} – {self.date}"

    def attendance_summary(self):
        total   = self.attendance_set.count()
        present = self.attendance_set.filter(attendance_status='Present').count()
        return {'total': total, 'present': present, 'absent': total - present}

    def topics_display(self):
        """Combined, human-readable list of everything covered this session."""
        parts = [t.title for t in self.topics.all()]
        if self.manual_topic:
            parts.append(self.manual_topic)
        return ', '.join(parts) if parts else (self.topic.title if self.topic else '—')


class Attendance(models.Model):
    STATUS_CHOICES = [('Present', 'Present'), ('Absent', 'Absent')]
    student           = models.ForeignKey(Student, on_delete=models.CASCADE)
    class_instance    = models.ForeignKey(Class, on_delete=models.CASCADE)
    date              = models.DateField()
    attendance_status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    note              = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('student', 'class_instance')

    def __str__(self):
        return f"{self.student.name} – {self.attendance_status}"


class WeeklyReport(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('submitted','Submitted'),('reviewed','Reviewed')]
    tutor             = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name="reports")
    week_start        = models.DateField()
    week_end          = models.DateField()
    classes_held      = models.PositiveIntegerField(default=0)
    students_attended = models.PositiveIntegerField(default=0)
    topics_covered    = models.TextField(blank=True)
    challenges        = models.TextField(blank=True)
    plan_next_week    = models.TextField(blank=True)
    admin_feedback    = models.TextField(blank=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('tutor', 'week_start')
        ordering = ['-week_start']

    def __str__(self):
        return f"{self.tutor.name} – Week of {self.week_start}"

    def auto_populate(self):
        classes = Class.objects.filter(tutor=self.tutor, date__range=[self.week_start, self.week_end])
        self.classes_held = classes.count()
        student_ids = Attendance.objects.filter(
            class_instance__in=classes, attendance_status='Present'
        ).values_list('student_id', flat=True).distinct()
        self.students_attended = len(set(student_ids))

        topics = []
        for c in classes:
            display = c.topics_display()
            if display and display != '—':
                topics.append(display)
        self.topics_covered = ', '.join(sorted(set(topics)))
        self.save()
