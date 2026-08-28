from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from datetime import date, timedelta
from django.contrib.auth.models import User
import secrets
import string
from .models import (
    Tutor, Student, Course, Topic, Class, Attendance,
    TimetableEntry, WeeklyReport, Classroom, Module
)
from .forms import (
    TutorLoginForm, TutorForm,
    StudentEditForm, AdminStudentEditForm,
    CourseForm, TopicForm,
    TutorClassForm, ClassroomSessionForm,
    TimetableEntryForm, TutorTimetableEntryForm,
    WeeklyReportForm, AdminFeedbackForm,
    ClassroomForm, TutorRegistrationForm, ModuleForm, AdminStudentAssignForm
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_staff or user.is_superuser

def get_week_range(offset=0):
    today = date.today() + timedelta(weeks=offset)
    start = today - timedelta(days=today.weekday())
    end   = start + timedelta(days=6)
    return start, end

def get_tutor_or_403(request):
    try:
        return request.user.tutor
    except Tutor.DoesNotExist:
        messages.error(request, "Tutor profile not found.")
        return None


# ─── Auth ─────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('admin_dashboard')
        if hasattr(request.user, 'tutor'):
            return redirect('tutor_dashboard')

    form = TutorLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']

        # Check if user exists but is inactive (pending approval)
        try:
            pending_user = User.objects.get(username=username)
            if not pending_user.is_active:
                messages.error(request, "Your account is pending admin approval.")
                return render(request, 'core/login.html', {'form': form})
        except User.DoesNotExist:
            pass

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if is_admin(user):
                return redirect('admin_dashboard')
            if hasattr(user, 'tutor'):
                return redirect('tutor_dashboard')
            messages.error(request, "No portal access assigned to this account.")
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ─────────────────────────────────────────────────────────────────────────────
# TUTOR DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def tutor_dashboard(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')

    today = date.today()
    week_start, week_end = get_week_range()

    week_classes = Class.objects.filter(
        tutor=tutor, date__range=[week_start, week_end]
    ).order_by('date', 'start_time')

    students   = Student.objects.filter(tutor=tutor, active=True)
    classrooms = Classroom.objects.filter(tutor=tutor, status='active')

    report, _ = WeeklyReport.objects.get_or_create(
        tutor=tutor, week_start=week_start,
        defaults={'week_end': week_end}
    )

    total_classes = Class.objects.filter(tutor=tutor).count()
    present_count = Attendance.objects.filter(
        class_instance__tutor=tutor, attendance_status='Present'
    ).count()
    total_att = Attendance.objects.filter(class_instance__tutor=tutor).count()
    rate      = round((present_count / total_att) * 100) if total_att else 0

    return render(request, 'core/tutor_dashboard.html', {
        'tutor':           tutor,
        'week_classes':    week_classes,
        'students':        students,
        'classrooms':      classrooms,
        'report':          report,
        'total_classes':   total_classes,
        'attendance_rate': rate,
        'week_start':      week_start,
        'week_end':        week_end,
        'today':           today,
    })


# ─── Tutor: Students ──────────────────────────────────────────────────────────

@login_required
def tutor_students(request):
    tutor    = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    students = Student.objects.filter(tutor=tutor).prefetch_related('courses', 'classrooms')
    return render(request, 'core/tutor_students.html', {
        'tutor': tutor, 'students': students
    })


@login_required
@user_passes_test(is_admin)
def admin_student_assign(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form = AdminStudentAssignForm(request.POST or None, student=student)
    if request.method == 'POST' and form.is_valid():
        tutor     = form.cleaned_data['tutor']
        classroom = form.cleaned_data['classroom']

        # pull student out of any classroom they were currently in
        for cr in student.classrooms.all():
            cr.students.remove(student)

        if classroom:
            classroom.students.add(student)
            # tutor follows the classroom unless the admin explicitly picked one
            student.tutor = tutor or classroom.tutor
        else:
            student.tutor = tutor

        student.save()

        messages.success(request, f"{student.name} assignment updated.")
        return redirect('admin_student_detail', pk=pk)

    return render(request, 'core/form.html', {
        'form': form, 'title': f'Assign — {student.name}', 'back_url': 'admin_students'
    })


@login_required
@user_passes_test(is_admin)
def admin_sync_students(request):
    if request.method == 'POST':
        from core.services.student_sync import sync_students
        try:
            created, updated = sync_students()
            messages.success(request, f"Sync complete — {created} created, {updated} updated.")
        except Exception as e:
            messages.error(request, f"Sync failed: {e}")
    return redirect('admin_students')



# core/views.py
@login_required
@user_passes_test(is_admin)
def admin_sync_courses(request):
    if request.method == 'POST':
        from core.services.course_sync import sync_courses, sync_modules
        try:
            cc, cu = sync_courses()
            mc, mu = sync_modules()
            messages.success(request, f"Courses: {cc} created/{cu} updated. Modules: {mc} created/{mu} updated.")
        except Exception as e:
            messages.error(request, f"Sync failed: {e}")
    return redirect('admin_courses')


@login_required
def tutor_student_detail(request, pk):
    tutor   = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    student = get_object_or_404(Student, pk=pk, tutor=tutor)

    # All classrooms this student is in (under this tutor)
    classrooms = student.classrooms.filter(tutor=tutor).select_related('course')

    # All sessions this student is in
    sessions = Class.objects.filter(
        students=student, tutor=tutor
    ).order_by('-date').select_related('topic', 'course', 'classroom')

    # All attendance records
    attendance_records = Attendance.objects.filter(
        student=student
    ).order_by('-date').select_related('class_instance__topic', 'class_instance__classroom')

    # Overall stats
    total_att   = attendance_records.count()
    present_att = attendance_records.filter(attendance_status='Present').count()
    absent_att  = total_att - present_att
    att_rate    = round((present_att / total_att) * 100) if total_att else 0

    # Resolve classroom display name for each session
    sessions_with_classroom = []
    for s in sessions:
        display_classroom = s.classroom
        if not display_classroom:
            # Find the student's classroom for this course
            display_classroom = classrooms.filter(course=s.course).first()
        sessions_with_classroom.append({
            'session':            s,
            'display_classroom':  display_classroom,
        })

    # Resolve classroom for each attendance record
    attendance_with_classroom = []
    for a in attendance_records:
        display_classroom = a.class_instance.classroom
        if not display_classroom:
            display_classroom = classrooms.filter(course=a.class_instance.course).first()
        attendance_with_classroom.append({
            'record':            a,
            'display_classroom': display_classroom,
        })

    # Per-classroom breakdown
    classroom_stats = []
    for cr in classrooms:
        # Match sessions directly linked to classroom OR standalone sessions for same course
        cr_sessions = Class.objects.filter(
            Q(classroom=cr) | Q(classroom__isnull=True, course=cr.course),
            students=student,
            tutor=tutor,
        )
        cr_total   = Attendance.objects.filter(
            student=student, class_instance__in=cr_sessions
        ).count()
        cr_present = Attendance.objects.filter(
            student=student, class_instance__in=cr_sessions,
            attendance_status='Present'
        ).count()
        classroom_stats.append({
            'classroom': cr,
            'sessions':  cr_sessions.count(),
            'present':   cr_present,
            'total':     cr_total,
            'rate':      round((cr_present / cr_total) * 100) if cr_total else 0,
        })

        

    return render(request, 'core/tutor_student_detail.html', {
        'tutor':             tutor,
        'student':           student,
        'classrooms':        classrooms,
        'sessions':          sessions,
        'attendance_records':attendance_records,
        'total_att':         total_att,
        'present_att':       present_att,
        'absent_att':        absent_att,
        'att_rate':          att_rate,
        'classroom_stats':   classroom_stats,
        'sessions_with_classroom': sessions_with_classroom,
        'attendance_with_classroom': attendance_with_classroom,
    })


@login_required
def tutor_student_edit(request, pk):
    tutor   = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    student = get_object_or_404(Student, pk=pk, tutor=tutor)
    form    = StudentEditForm(request.POST or None, instance=student)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Student updated.")
        return redirect('tutor_student_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit — {student.name}', 'back_url': 'tutor_students'
    })


@login_required
def tutor_student_delete(request, pk):
    tutor   = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    student = get_object_or_404(Student, pk=pk, tutor=tutor)
    if request.method == 'POST':
        student.delete()
        messages.success(request, "Student removed.")
        return redirect('tutor_students')
    return render(request, 'core/confirm_delete.html', {
        'obj': student, 'back': 'tutor_students'
    })


# ─── Tutor: Classrooms ────────────────────────────────────────────────────────

@login_required
def tutor_classrooms(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    status_filter = request.GET.get('status', '')
    classrooms = Classroom.objects.filter(tutor=tutor).prefetch_related('students', 'sessions')
    if status_filter:
        classrooms = classrooms.filter(status=status_filter)

    # Annotate counts so the template can use them without hitting DB per row
    from django.db.models import Count
    classrooms = classrooms.annotate(
        student_count=Count('students', distinct=True),
        session_count=Count('sessions', distinct=True),
    )

    return render(request, 'core/tutor_classrooms.html', {
        'tutor': tutor, 'classrooms': classrooms, 'status_filter': status_filter,
    })





@login_required
def tutor_classroom_detail(request, pk):
    tutor     = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    classroom = get_object_or_404(Classroom, pk=pk, tutor=tutor)
    sessions  = classroom.sessions.order_by('-date', '-start_time')
    students  = classroom.students.all()

    student_stats = []
    for student in students:
        total   = Attendance.objects.filter(
            class_instance__in=sessions, student=student
        ).count()
        present = Attendance.objects.filter(
            class_instance__in=sessions, student=student,
            attendance_status='Present'
        ).count()
        student_stats.append({
            'student': student,
            'total':   total,
            'present': present,
            'rate':    round((present / total) * 100) if total else 0,
        })

    return render(request, 'core/tutor_classroom_detail.html', {
        'tutor':         tutor,
        'classroom':     classroom,
        'sessions':      sessions,
        'students':      students,
        'student_stats': student_stats,
    })








@login_required
def tutor_classroom_session_create(request, pk):
    tutor     = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    classroom = get_object_or_404(Classroom, pk=pk, tutor=tutor)
    form      = ClassroomSessionForm(classroom=classroom, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        topics = form.cleaned_data.get('topics')

        session              = form.save(commit=False)
        session.tutor        = tutor
        session.course       = classroom.course
        session.classroom    = classroom
        session.manual_topic = form.cleaned_data.get('manual_topic', '')
        session.topic        = topics.first() if topics else None  # mirror for legacy single-topic reads
        session.save()

        if topics:
            session.topics.set(topics)
        session.students.set(classroom.students.all())

        messages.success(request, "Session posted.")
        return redirect('tutor_classroom_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'New Session — {classroom.name}', 'back_url': 'tutor_classrooms'
    })


@login_required
def tutor_classroom_session_attendance(request, pk, spk):
    tutor     = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    classroom = get_object_or_404(Classroom, pk=pk, tutor=tutor)
    session   = get_object_or_404(Class, pk=spk, classroom=classroom)
    existing  = {a.student_id: a for a in Attendance.objects.filter(class_instance=session)}

    if request.method == 'POST':
        for student in classroom.students.all():
            status = request.POST.get(f'student_{student.pk}', 'Absent')
            note   = request.POST.get(f'note_{student.pk}', '')
            if student.pk in existing:
                rec                   = existing[student.pk]
                rec.attendance_status = status
                rec.note              = note
                rec.save()
            else:
                Attendance.objects.create(
                    student=student, class_instance=session,
                    date=session.date, attendance_status=status, note=note,
                )
        messages.success(request, "Attendance saved.")
        return redirect('tutor_classroom_detail', pk=pk)

    return render(request, 'core/classroom_attendance.html', {
        'tutor':     tutor,
        'classroom': classroom,
        'session':   session,
        'students':  classroom.students.all(),
        'existing':  existing,
    })


# ─── Tutor: Standalone Classes ────────────────────────────────────────────────

@login_required
def tutor_classes(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    classes = Class.objects.filter(tutor=tutor).order_by('-date')
    return render(request, 'core/tutor_classes.html', {'tutor': tutor, 'classes': classes})


@login_required
def tutor_class_create(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    form = TutorClassForm(tutor=tutor, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cls       = form.save(commit=False)
        cls.tutor = tutor

        # Auto-link to classroom based on selected course + students
        if cls.course:
            selected_students = form.cleaned_data.get('students', [])
            classroom = Classroom.objects.filter(
                tutor=tutor,
                course=cls.course,
                status='active',
                students__in=selected_students,
            ).distinct().first()
            if classroom:
                cls.classroom = classroom

        cls.save()
        form.save_m2m()
        messages.success(request, "Session created.")
        return redirect('tutor_classes')
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Create Session', 'back_url': 'tutor_classes'
    })


@login_required
def tutor_class_detail(request, pk):
    tutor              = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    cls                = get_object_or_404(Class, pk=pk, tutor=tutor)
    attendance_records = Attendance.objects.filter(class_instance=cls)
    summary            = cls.attendance_summary()
    return render(request, 'core/class_detail.html', {
        'cls': cls, 'attendance_records': attendance_records,
        'summary': summary, 'tutor': tutor,
    })


@login_required
def tutor_class_edit(request, pk):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    cls  = get_object_or_404(Class, pk=pk, tutor=tutor)
    form = TutorClassForm(tutor=tutor, data=request.POST or None, instance=cls)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Session updated.")
        return redirect('tutor_class_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Edit Session', 'back_url': 'tutor_classes'
    })


@login_required
def tutor_class_delete(request, pk):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    cls = get_object_or_404(Class, pk=pk, tutor=tutor)
    if request.method == 'POST':
        cls.delete()
        messages.success(request, "Session deleted.")
        return redirect('tutor_classes')
    return render(request, 'core/confirm_delete.html', {'obj': cls, 'back': 'tutor_classes'})


@login_required
def take_attendance(request, class_pk):
    tutor    = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    cls      = get_object_or_404(Class, pk=class_pk, tutor=tutor)
    existing = {a.student_id: a for a in Attendance.objects.filter(class_instance=cls)}

    if request.method == 'POST':
        for student in cls.students.all():
            status = request.POST.get(f'student_{student.pk}', 'Absent')
            note   = request.POST.get(f'note_{student.pk}', '')
            if student.pk in existing:
                rec                   = existing[student.pk]
                rec.attendance_status = status
                rec.note              = note
                rec.save()
            else:
                Attendance.objects.create(
                    student=student, class_instance=cls,
                    date=cls.date, attendance_status=status, note=note,
                )
        messages.success(request, "Attendance saved.")
        return redirect('tutor_class_detail', pk=class_pk)

    return render(request, 'core/take_attendance.html', {
        'cls': cls, 'students': cls.students.all(),
        'existing': existing, 'tutor': tutor,
    })


# ─── API: topics for JS dropdown ─────────────────────────────────────────────

@login_required
def api_course_topics(request, course_pk):
    topics = Topic.objects.filter(course_id=course_pk).order_by(
        'module__order', 'week', 'day'
    ).values('id', 'title', 'week', 'day', 'module__name', 'module__id')
    return JsonResponse({'topics': list(topics)})


# ─── API: classrooms for a tutor (used by add-student JS) ────────────────────

@login_required
def api_tutor_classrooms(request, tutor_pk):
    classrooms = Classroom.objects.filter(
        tutor_id=tutor_pk, status='active'
    ).select_related('course').values('id', 'name', 'course__name')
    data = [
        {'id': cr['id'], 'name': f"{cr['name']} ({cr['course__name']})"}
        for cr in classrooms
    ]
    return JsonResponse({'classrooms': data})


# ─── Tutor: Timetable ────────────────────────────────────────────────────────

@login_required
def tutor_timetable(request):
    tutor   = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    entries = TimetableEntry.objects.filter(tutor=tutor).order_by('day_of_week', 'start_time')
    days    = dict(TimetableEntry.DAYS)
    grouped = {i: [] for i in range(7)}
    for e in entries:
        grouped[e.day_of_week].append(e)
    return render(request, 'core/tutor_timetable.html', {
        'tutor': tutor, 'grouped': grouped, 'days': days,
    })


@login_required
def tutor_timetable_create(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    form = TutorTimetableEntryForm(tutor=tutor, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        entry       = form.save(commit=False)
        entry.tutor = tutor
        try:
            entry.full_clean()
            entry.save()
            form.save_m2m()
            messages.success(request, "Entry added.")
            return redirect('tutor_timetable')
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Add Timetable Entry', 'back_url': 'tutor_timetable'
    })


@login_required
def tutor_timetable_edit(request, pk):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    entry = get_object_or_404(TimetableEntry, pk=pk, tutor=tutor)
    form  = TutorTimetableEntryForm(tutor=tutor, data=request.POST or None, instance=entry)
    if request.method == 'POST' and form.is_valid():
        try:
            e       = form.save(commit=False)
            e.tutor = tutor
            e.full_clean()
            e.save()
            form.save_m2m()
            messages.success(request, "Updated.")
            return redirect('tutor_timetable')
        except Exception as ex:
            messages.error(request, str(ex))
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Edit Timetable Entry', 'back_url': 'tutor_timetable'
    })


@login_required
def tutor_timetable_delete(request, pk):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    entry = get_object_or_404(TimetableEntry, pk=pk, tutor=tutor)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, "Deleted.")
        return redirect('tutor_timetable')
    return render(request, 'core/confirm_delete.html', {'obj': entry, 'back': 'tutor_timetable'})


# ─── Tutor: Reports ───────────────────────────────────────────────────────────

@login_required
def tutor_reports(request):
    tutor   = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    reports = WeeklyReport.objects.filter(tutor=tutor)
    return render(request, 'core/tutor_reports.html', {'tutor': tutor, 'reports': reports})


@login_required
def tutor_report_create(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')

    week_start, week_end = get_week_range()
    report, created = WeeklyReport.objects.get_or_create(
        tutor=tutor, week_start=week_start,
        defaults={'week_end': week_end}
    )

    if request.method == 'GET':
        report.auto_populate()  # always refresh before showing the form

    form = WeeklyReportForm(request.POST or None, instance=report)
    if request.method == 'POST' and form.is_valid():
        r        = form.save(commit=False)
        r.status = 'submitted'
        r.save()
        messages.success(request, "Report submitted!")
        return redirect('tutor_reports')

    return render(request, 'core/report_form.html', {
        'form': form, 'report': report, 'tutor': tutor
    })


@login_required
def tutor_report_edit(request, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    report = get_object_or_404(WeeklyReport, pk=pk, tutor=tutor)

    if request.method == 'GET':
        report.auto_populate()  # refresh numbers before showing the form

    form = WeeklyReportForm(request.POST or None, instance=report)
    if request.method == 'POST' and form.is_valid():
        r        = form.save(commit=False)
        r.status = 'submitted'
        r.save()
        messages.success(request, "Report updated.")
        return redirect('tutor_reports')

    return render(request, 'core/report_form.html', {
        'form': form, 'report': report, 'tutor': tutor
    })


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    today = date.today()
    week_start, week_end = get_week_range()

    total_tutors      = Tutor.objects.filter(active=True).count()
    online_tutors     = Tutor.objects.filter(active=True, mode='online').count()
    physical_tutors   = Tutor.objects.filter(active=True, mode='physical').count()
    total_students    = Student.objects.filter(active=True).count()
    online_students   = Student.objects.filter(active=True, mode='online').count()
    physical_students = Student.objects.filter(active=True, mode='physical').count()
    week_classes      = Class.objects.filter(date__range=[week_start, week_end]).count()
    total_present     = Attendance.objects.filter(
        date__range=[week_start, week_end], attendance_status='Present'
    ).count()
    total_att         = Attendance.objects.filter(date__range=[week_start, week_end]).count()
    week_rate         = round((total_present / total_att) * 100) if total_att else 0
    pending_reports   = WeeklyReport.objects.filter(status='submitted').count()
    recent_reports    = WeeklyReport.objects.filter(status='submitted').select_related('tutor')[:5]
    active_classrooms = Classroom.objects.filter(status='active').count()

    tutors = Tutor.objects.filter(active=True).annotate(
        student_count=Count('students'),
        class_count=Count('classes')
    )

    return render(request, 'core/admin_dashboard.html', {
        'total_tutors': total_tutors, 'online_tutors': online_tutors,
        'physical_tutors': physical_tutors, 'total_students': total_students,
        'online_students': online_students, 'physical_students': physical_students,
        'week_classes': week_classes, 'week_rate': week_rate,
        'pending_reports': pending_reports, 'recent_reports': recent_reports,
        'active_classrooms': active_classrooms,
        'tutors': tutors, 'today': today,
    })


# ─── Admin: Tutors ────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_tutors(request):
    mode_filter = request.GET.get('mode', '')

    tutors = Tutor.objects.select_related('user').annotate(
        student_count=Count('students')
    )

    if mode_filter:
        tutors = tutors.filter(mode=mode_filter)

    return render(request, 'core/admin_tutors.html', {
        'tutors': tutors,
        'mode_filter': mode_filter
    })


@login_required
@user_passes_test(is_admin)
def admin_tutor_detail(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    week_start, week_end = get_week_range()
    return render(request, 'core/admin_tutor_detail.html', {
        'tutor':       tutor,
        'week_classes':Class.objects.filter(tutor=tutor, date__range=[week_start, week_end]),
        'students':    Student.objects.filter(tutor=tutor),
        'reports':     WeeklyReport.objects.filter(tutor=tutor)[:5],
        'timetable':   TimetableEntry.objects.filter(tutor=tutor),
        'classrooms':  Classroom.objects.filter(tutor=tutor),
    })


from django.contrib.auth.models import User
import secrets
import string

@login_required
@user_passes_test(is_admin)
def admin_tutor_create(request):
    form = TutorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # Generate a secure random password
        alphabet = string.ascii_letters + string.digits
        raw_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        # Create the User account
        user = User.objects.create_user(
            username=form.cleaned_data['username'],   # TutorForm must have this field
            password=raw_password,
            first_name=form.cleaned_data.get('first_name', ''),
            last_name=form.cleaned_data.get('last_name', ''),
            email=form.cleaned_data.get('email', ''),
        )

        # Create the Tutor profile linked to the user

        tutor = form.save(commit=False)
        tutor.user = user
        tutor.specialization = form.cleaned_data.get('specialization', '')
        tutor.save()
        form.save_m2m()

        messages.success(
            request,
            f"Tutor '{user.get_full_name() or user.username}' created. "
            f"Share these login credentials: "
            f"Username: {user.username} | Password: {raw_password}"
        )
        return redirect('admin_tutor_detail', pk=tutor.pk)

    return render(request, 'core/form.html', {
        'form': form, 'title': 'Add Tutor', 'back_url': 'admin_tutors'
    })


@login_required
@user_passes_test(is_admin)
def admin_tutor_edit(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    form  = TutorForm(request.POST or None, instance=tutor)
    if request.method == 'POST' and form.is_valid():
        # Update the linked User's account fields
        user            = tutor.user
        user.username   = form.cleaned_data['username']
        user.first_name = form.cleaned_data.get('first_name', '')
        user.last_name  = form.cleaned_data.get('last_name', '')
        user.email      = form.cleaned_data.get('email', '')
        user.save()

        form.save()
        messages.success(request, "Tutor updated.")
        return redirect('admin_tutor_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Edit Tutor', 'back_url': 'admin_tutors'
    })


@login_required
@user_passes_test(is_admin)
def admin_tutor_delete(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    if request.method == 'POST':
        tutor.delete()
        messages.success(request, "Tutor removed.")
        return redirect('admin_tutors')
    return render(request, 'core/confirm_delete.html', {'obj': tutor, 'back': 'admin_tutors'})


@login_required
@user_passes_test(is_admin)
def admin_tutor_reset_password(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)

    if request.method == 'POST':
        alphabet     = string.ascii_letters + string.digits
        raw_password = ''.join(secrets.choice(alphabet) for _ in range(12))

        if tutor.user is None:
            # ── Tutor was created before the new auth flow ─────────────────
            # Derive a username from their name/phone, ensure it's unique
            base_username = (
                tutor.name.lower().replace(' ', '_')
                if hasattr(tutor, 'name') and tutor.name
                else f"tutor_{tutor.pk}"
            )
            username = base_username
            counter  = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                password=raw_password,
            )
            tutor.user = user
            tutor.save()

            messages.success(
                request,
                f"User account created for this tutor. "
                f"Username: {username} | Password: {raw_password}"
            )
        else:
            # ── Normal reset ───────────────────────────────────────────────
            tutor.user.set_password(raw_password)
            tutor.user.save()

            messages.success(
                request,
                f"Password reset. "
                f"Username: {tutor.user.username} | Password: {raw_password}"
            )

        return redirect('admin_tutor_detail', pk=pk)

    # GET — confirmation page
    return render(request, 'core/confirm_action.html', {
        'message': (
            f"Create login credentials for {tutor}?"
            if tutor.user is None
            else f"Reset password for {tutor.user.get_full_name() or tutor.user.username}?"
        ),
        'back': 'admin_tutors',
    })



# ─── Admin: Students ──────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_students(request):
    mode_filter  = request.GET.get('mode', '')
    tutor_filter = request.GET.get('tutor', '')
    students = Student.objects.select_related('tutor').prefetch_related('courses', 'classrooms')
    if mode_filter:
        students = students.filter(mode=mode_filter)
    if tutor_filter:
        students = students.filter(tutor_id=tutor_filter)
    return render(request, 'core/admin_students.html', {
        'students':     students,
        'mode_filter':  mode_filter,
        'tutor_filter': tutor_filter,
        'tutors':       Tutor.objects.filter(active=True),
    })





@login_required
@user_passes_test(is_admin)
def admin_student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    classrooms = student.classrooms.all().select_related('course', 'tutor')
    sessions   = Class.objects.filter(
        students=student
    ).order_by('-date').select_related('topic', 'course', 'classroom', 'tutor')

    attendance_records = Attendance.objects.filter(
        student=student
    ).order_by('-date').select_related('class_instance__topic', 'class_instance__classroom')

    total_att   = attendance_records.count()
    present_att = attendance_records.filter(attendance_status='Present').count()
    absent_att  = total_att - present_att
    att_rate    = round((present_att / total_att) * 100) if total_att else 0

    # Resolve classroom for each attendance record
    attendance_with_classroom = []
    for a in attendance_records:
        display_classroom = a.class_instance.classroom
        if not display_classroom:
            display_classroom = classrooms.filter(course=a.class_instance.course).first()
        attendance_with_classroom.append({
            'record':            a,
            'display_classroom': display_classroom,
        })

    classroom_stats = []
    for cr in classrooms:
        cr_sessions = sessions.filter(classroom=cr)
        cr_total    = Attendance.objects.filter(
            student=student, class_instance__in=cr_sessions
        ).count()
        cr_present  = Attendance.objects.filter(
            student=student, class_instance__in=cr_sessions,
            attendance_status='Present'
        ).count()
        classroom_stats.append({
            'classroom': cr,
            'sessions':  cr_sessions.count(),
            'present':   cr_present,
            'total':     cr_total,
            'rate':      round((cr_present / cr_total) * 100) if cr_total else 0,
        })

    return render(request, 'core/admin_student_detail.html', {
        'student':            student,
        'classrooms':         classrooms,
        'sessions':           sessions,
        'attendance_records': attendance_records,
        'total_att':          total_att,
        'present_att':        present_att,
        'absent_att':         absent_att,
        'att_rate':           att_rate,
        'classroom_stats':    classroom_stats,
        'attendance_with_classroom': attendance_with_classroom,
    })


@login_required
@user_passes_test(is_admin)
def admin_student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    form    = AdminStudentEditForm(request.POST or None, instance=student)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Student updated.")
        return redirect('admin_student_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit — {student.name}', 'back_url': 'admin_students'
    })


@login_required
@user_passes_test(is_admin)
def admin_student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.delete()
        messages.success(request, "Student removed.")
        return redirect('admin_students')
    return render(request, 'core/confirm_delete.html', {'obj': student, 'back': 'admin_students'})


# ─── Admin: Classrooms ────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_classrooms(request):
    mode_filter   = request.GET.get('mode', '')
    status_filter = request.GET.get('status', '')
    tutor_filter  = request.GET.get('tutor', '')
    classrooms = Classroom.objects.select_related('tutor', 'course').prefetch_related('students')
    if mode_filter:   classrooms = classrooms.filter(tutor__mode=mode_filter)
    if status_filter: classrooms = classrooms.filter(status=status_filter)
    if tutor_filter:  classrooms = classrooms.filter(tutor_id=tutor_filter)
    return render(request, 'core/admin_classrooms.html', {
        'classrooms': classrooms, 'tutors': Tutor.objects.filter(active=True),
        'mode_filter': mode_filter, 'status_filter': status_filter, 'tutor_filter': tutor_filter,
    })


@login_required
@user_passes_test(is_admin)
def admin_classroom_detail(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    sessions  = classroom.sessions.order_by('-date')
    students  = classroom.students.all()
    student_stats = []
    for student in students:
        total   = Attendance.objects.filter(class_instance__in=sessions, student=student).count()
        present = Attendance.objects.filter(
            class_instance__in=sessions, student=student, attendance_status='Present'
        ).count()
        student_stats.append({
            'student': student, 'total': total, 'present': present,
            'rate': round((present / total) * 100) if total else 0,
        })
    return render(request, 'core/admin_classroom_detail.html', {
        'classroom': classroom, 'sessions': sessions,
        'students': students, 'student_stats': student_stats,
    })


# ─── Admin: Timetable ────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_timetable(request):
    mode_filter     = request.GET.get('mode', '')
    location_filter = request.GET.get('location', '')

    entries = TimetableEntry.objects.select_related(
        'tutor', 'course'
    ).order_by('day_of_week', 'start_time')

    if mode_filter:
        entries = entries.filter(tutor__mode=mode_filter)
    if location_filter:
        entries = entries.filter(location=location_filter)

    days    = dict(TimetableEntry.DAYS)
    grouped = {i: [] for i in range(7)}
    for e in entries:
        grouped[e.day_of_week].append(e)

    return render(request, 'core/admin_timetable.html', {
        'grouped':          grouped,
        'days':             days,
        'mode_filter':      mode_filter,
        'location_filter':  location_filter,
    })


@login_required
@user_passes_test(is_admin)
def admin_timetable_create(request):
    form = TimetableEntryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        entry = form.save(commit=False)
        try:
            entry.full_clean(); entry.save(); form.save_m2m()
            messages.success(request, "Entry added.")
            return redirect('admin_timetable')
        except Exception as e:
            messages.error(request, str(e))
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Add Timetable Entry', 'back_url': 'admin_timetable'
    })


@login_required
@user_passes_test(is_admin)
def admin_timetable_edit(request, pk):
    entry = get_object_or_404(TimetableEntry, pk=pk)
    form  = TimetableEntryForm(request.POST or None, instance=entry)
    if request.method == 'POST' and form.is_valid():
        try:
            e = form.save(commit=False)
            e.full_clean(); e.save(); form.save_m2m()
            messages.success(request, "Updated.")
            return redirect('admin_timetable')
        except Exception as ex:
            messages.error(request, str(ex))
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Edit Timetable Entry', 'back_url': 'admin_timetable'
    })


@login_required
@user_passes_test(is_admin)
def admin_timetable_delete(request, pk):
    entry = get_object_or_404(TimetableEntry, pk=pk)
    if request.method == 'POST':
        entry.delete(); messages.success(request, "Deleted.")
        return redirect('admin_timetable')
    return render(request, 'core/confirm_delete.html', {'obj': entry, 'back': 'admin_timetable'})


# ─── Admin: Reports ───────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_reports(request):
    mode_filter   = request.GET.get('mode', '')
    status_filter = request.GET.get('status', '')
    reports = WeeklyReport.objects.select_related('tutor').order_by('-week_start')
    if mode_filter:   reports = reports.filter(tutor__mode=mode_filter)
    if status_filter: reports = reports.filter(status=status_filter)
    return render(request, 'core/admin_reports.html', {
        'reports': reports, 'mode_filter': mode_filter, 'status_filter': status_filter
    })


@login_required
@user_passes_test(is_admin)
def admin_report_detail(request, pk):
    report = get_object_or_404(WeeklyReport, pk=pk)
    form   = AdminFeedbackForm(request.POST or None, instance=report)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Feedback saved.")
        return redirect('admin_reports')

    # All classes this tutor held during the report week
    classes = Class.objects.filter(
        tutor=report.tutor,
        date__range=[report.week_start, report.week_end]
    ).select_related('course', 'classroom').prefetch_related('students', 'topics')

    # Build per-course breakdown
    course_breakdown = {}
    # core/views.py — inside admin_report_detail
    for cls in classes:
        cid = cls.course_id
        if cid not in course_breakdown:
            course_breakdown[cid] = {
                'course':    cls.course,
                'sessions':  [],
                'topics':    set(),
                'students':  set(),
                'present':   0,
                'total_att': 0,
            }
        entry = course_breakdown[cid]
        entry['sessions'].append(cls)

        # was: if cls.topic: entry['topics'].add(cls.topic.title)
        for t in cls.topics.all():
            entry['topics'].add(t.title)
        if cls.manual_topic:
            entry['topics'].add(cls.manual_topic)

        for student in cls.students.all():
            entry['students'].add(student.pk)

        att = Attendance.objects.filter(class_instance=cls)
        entry['total_att'] += att.count()
        entry['present']   += att.filter(attendance_status='Present').count()

    # Convert to list with computed values
    course_summary = []
    for data in course_breakdown.values():
        total_att = data['total_att']
        present   = data['present']
        course_summary.append({
            'course':       data['course'],
            'session_count': len(data['sessions']),
            'sessions':     sorted(data['sessions'], key=lambda s: s.date),
            'topics':       sorted(data['topics']),
            'student_count': len(data['students']),
            'present':      present,
            'total_att':    total_att,
            'att_rate':     round((present / total_att) * 100) if total_att else 0,
        })
    total_topics = sum(len(c['topics']) for c in course_summary)
    return render(request, 'core/admin_report_detail.html', {
        'report':          report,
        'form':            form,
        'course_summary':  course_summary,
        'total_sessions':  classes.count(),
        'total_topics':   total_topics,
    })


# ─── Admin: Courses + Topics ──────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_courses(request):
    courses = Course.objects.annotate(
        student_count=Count('students', distinct=True),
        topic_count=Count('topics', distinct=True),
        module_count=Count('modules', distinct=True),
    )
    return render(request, 'core/admin_courses.html', {'courses': courses})


@login_required
@user_passes_test(is_admin)
def admin_course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, "Course created.")
        return redirect('admin_courses')
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Add Course', 'back_url': 'admin_courses'
    })



@login_required
@user_passes_test(is_admin)
def admin_course_detail(request, pk):
    course  = get_object_or_404(Course, pk=pk)
    modules = Module.objects.filter(course=course).prefetch_related('topics')
    # Topics with no module
    orphan_topics = Topic.objects.filter(course=course, module__isnull=True).order_by('week', 'day')
    return render(request, 'core/admin_course_detail.html', {
        'course': course, 'modules': modules, 'orphan_topics': orphan_topics
    })


@login_required
@user_passes_test(is_admin)
def admin_course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    form   = CourseForm(request.POST or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, "Course updated.")
        return redirect('admin_courses')
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Edit Course', 'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete(); messages.success(request, "Course deleted.")
        return redirect('admin_courses')
    return render(request, 'core/confirm_delete.html', {'obj': course, 'back': 'admin_courses'})


@login_required
@user_passes_test(is_admin)
def admin_topic_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    form   = TopicForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        topic = form.save(commit=False)
        topic.course = course; topic.save()
        messages.success(request, f"Topic added to {course.name}.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Add Topic — {course.name}', 'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_topic_edit(request, course_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    form   = TopicForm(request.POST or None, instance=topic)
    if request.method == 'POST' and form.is_valid():
        form.save(); messages.success(request, "Topic updated.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit Topic — {course.name}', 'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_topic_delete(request, course_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    if request.method == 'POST':
        topic.delete(); messages.success(request, "Topic deleted.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {'obj': topic, 'back': 'admin_courses'})






# ─── Tutor: Courses + Topics ──────────────────────────────────────────────────

@login_required
def tutor_courses(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    courses = Course.objects.annotate(
        student_count=Count('students', distinct=True),
        topic_count=Count('topics', distinct=True),
        module_count=Count('modules', distinct=True),
    )
    return render(request, 'core/tutor_courses.html', {
        'tutor': tutor, 'courses': courses
    })


@login_required
def tutor_course_create(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    form = CourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Course created.")
        return redirect('tutor_courses')
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Add Course', 'back_url': 'tutor_courses'
    })


@login_required
def tutor_course_detail(request, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    course = get_object_or_404(Course, pk=pk)
    modules = Module.objects.filter(course=course).prefetch_related('topics')
    orphan_topics = Topic.objects.filter(course=course, module__isnull=True).order_by('week', 'day')

    return render(request, 'core/tutor_course_detail.html', {
        'tutor':         tutor,
        'course':        course,
        'modules':       modules,        # ← was missing
        'orphan_topics': orphan_topics,  # ← was missing
    })



@login_required
def tutor_course_edit(request, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    course = get_object_or_404(Course, pk=pk)
    form   = CourseForm(request.POST or None, instance=course)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Course updated.")
        return redirect('tutor_course_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit — {course.name}', 'back_url': 'tutor_courses'
    })


@login_required
def tutor_course_delete(request, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        messages.success(request, "Course deleted.")
        return redirect('tutor_courses')
    return render(request, 'core/confirm_delete.html', {
        'obj': course, 'back': 'tutor_courses'
    })


@login_required
def tutor_topic_create(request, course_pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    form   = TopicForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        topic        = form.save(commit=False)
        topic.course = course
        topic.save()
        messages.success(request, f"Topic added to {course.name}.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form,
        'title': f'Add Topic — {course.name}',
        'back_url': 'tutor_courses'
    })


@login_required
def tutor_topic_edit(request, course_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    form   = TopicForm(request.POST or None, instance=topic)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Topic updated.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form,
        'title': f'Edit Topic — {course.name}',
        'back_url': 'tutor_courses'
    })


@login_required
def tutor_topic_delete(request, course_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    if request.method == 'POST':
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': topic, 'back': 'tutor_courses'
    })




    from django.contrib.auth import update_session_auth_hash

@login_required
def tutor_change_password(request):
    tutor = get_tutor_or_403(request)
    if not tutor:
        return redirect('login')

    if request.method == 'POST':
        current  = request.POST.get('current_password', '')
        new      = request.POST.get('new_password', '')
        confirm  = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, "Current password is incorrect.")
        elif len(new) < 8:
            messages.error(request, "New password must be at least 8 characters.")
        elif new != confirm:
            messages.error(request, "New passwords do not match.")
        else:
            request.user.set_password(new)
            request.user.save()
            # Keep the tutor logged in after password change
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")
            return redirect('tutor_dashboard')

    return render(request, 'core/tutor_change_password.html', {'tutor': tutor})





def tutor_register(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('admin_dashboard')
        if hasattr(request.user, 'tutor'):
            return redirect('tutor_dashboard')

    form = TutorRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data

        # Create User (inactive until approved)
        user = User.objects.create_user(
            username   = cd['username'],
            password   = cd['password'],
            first_name = cd['first_name'],
            last_name  = cd['last_name'],
            email      = cd['email'],
            is_active  = False,   # can't log in until approved
        )

        # Create Tutor profile
        Tutor.objects.create(
            user           = user,
            phone          = cd.get('phone', ''),
            specialization = cd.get('specialization', ''),
            mode           = cd['mode'],
            bio            = cd.get('bio', ''),
            active         = True,
            is_approved    = False,
        )

        messages.success(
            request,
            "Registration submitted! You'll be able to log in once an admin approves your account."
        )
        return redirect('login')

    return render(request, 'core/tutor_register.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def admin_tutor_approve(request, pk):
    tutor = get_object_or_404(Tutor, pk=pk)
    if request.method == 'POST':
        tutor.is_approved    = True
        tutor.user.is_active = True
        tutor.user.save()
        tutor.save()
        messages.success(request, f"{tutor.name} has been approved and can now log in.")
        return redirect('admin_tutor_detail', pk=pk)
    return render(request, 'core/confirm_action.html', {
        'message': f"Approve {tutor.name} and grant login access?",
        'back':    'admin_tutors',
    })





@login_required
@user_passes_test(is_admin)
def admin_change_password(request):
    if request.method == 'POST':
        current = request.POST.get('current_password', '')
        new     = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, "Current password is incorrect.")
        elif len(new) < 8:
            messages.error(request, "New password must be at least 8 characters.")
        elif new != confirm:
            messages.error(request, "New passwords do not match.")
        else:
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")
            return redirect('admin_dashboard')

    return render(request, 'core/admin_change_password.html')




from django.utils.timezone import now

@login_required
@user_passes_test(is_admin)
def admin_student_report(request, pk):
    from collections import defaultdict

    student    = get_object_or_404(Student, pk=pk)
    classrooms = student.classrooms.all().select_related('course', 'tutor')
    classroom  = classrooms.first()
    tutor      = student.tutor

    # Sessions + attendance
    sessions = Class.objects.filter(
        students=student
    ).order_by('date').select_related('course', 'classroom').prefetch_related('topics')

    attendance_records = Attendance.objects.filter(
        student=student
    ).select_related('class_instance__topic', 'class_instance__classroom')

    total_att   = attendance_records.count()
    present_att = attendance_records.filter(attendance_status='Present').count()
    absent_att  = total_att - present_att
    att_rate    = round((present_att / total_att) * 100) if total_att else 0

    # Grade logic
    if att_rate >= 90:   grade, grade_label = 'A+', 'Outstanding'
    elif att_rate >= 80: grade, grade_label = 'A',  'Strong Progress'
    elif att_rate >= 70: grade, grade_label = 'B',  'Good Progress'
    elif att_rate >= 60: grade, grade_label = 'C',  'Satisfactory'
    else:                grade, grade_label = 'D',  'Needs Improvement'

    # Per-classroom breakdown
    classroom_stats = []
    for cr in classrooms:
        cr_sessions = sessions.filter(classroom=cr)
        cr_total    = attendance_records.filter(class_instance__in=cr_sessions).count()
        cr_present  = attendance_records.filter(
            class_instance__in=cr_sessions, attendance_status='Present'
        ).count()
        classroom_stats.append({
            'classroom': cr.name,
            'rate':      round((cr_present / cr_total) * 100) if cr_total else 0,
        })

    # Topics covered — grouped by module
    topics = Topic.objects.filter(
        classes__in=sessions
    ).distinct().select_related('module').order_by('module__order', 'week', 'day')

    topic_tags = list(topics.values_list('title', flat=True))

    module_groups = defaultdict(list)
    for t in topics:
        module_name = t.module.name if t.module else 'General'
        module_groups[module_name].append(t.title)

    modules = [
        {
            'title':    mod_name,
            'subtitle': f'{len(topic_list)} topic{"s" if len(topic_list) != 1 else ""}',
            'topics':   topic_list,
        }
        for mod_name, topic_list in module_groups.items()
    ]

    # Session log rows
    # core/views.py — inside admin_student_report
    att_map = {a.class_instance_id: a for a in attendance_records}
    session_log = []
    for s in sessions:
        att = att_map.get(s.pk)
        session_log.append({
            'date':         s.date.strftime('%b %d, %Y'),
            'topic':        s.topics_display(),   # was: s.topic.title if s.topic else s.course.name
            'classroom':    s.classroom.name if s.classroom else '—',
            'status':       att.attendance_status if att else 'No record',
            'status_class': att.attendance_status.lower() if att else 'draft',
            'note':         att.note if att and att.note else '—',
        })

    # Tutor comment from most recent weekly report
    tutor_comment = ''
    if tutor:
        latest_report = WeeklyReport.objects.filter(tutor=tutor).order_by('-week_start').first()
        if latest_report and latest_report.challenges:
            tutor_comment = latest_report.challenges

    # Weeks completed
    weeks_completed = 0
    if classroom and classroom.start_date:
        weeks_completed = max(1, ((now().date() - classroom.start_date).days // 7) + 1)

    context = {
        'student_name':        student.name,
        'student_initial':     student.name[0].upper() if student.name else '?',
        'course_name':         classroom.course.name if classroom else '—',
        'classroom_name':      classroom.name if classroom else '—',
        'tutor_name':          tutor.name if tutor else '—',
        'mode':                student.get_mode_display(),
        'enrolled_date':       student.enrolled_at.strftime('%b %d, %Y') if hasattr(student, 'enrolled_at') and student.enrolled_at else '—',
        'generated_date':      now().strftime('%B %d, %Y'),
        'report_period':       f"{sessions.first().date.strftime('%b %d, %Y') if sessions.exists() else '—'} – {now().strftime('%b %d, %Y')}",
        'weeks_completed':     weeks_completed,
        'total_sessions':      total_att,
        'topics_count':        len(topic_tags),
        'attendance_rate':     att_rate,
        'present_count':       present_att,
        'absent_count':        absent_att,
        'current_week':        weeks_completed,
        'grade':               grade,
        'grade_label':         grade_label,
        'performance_summary': f"{student.name.split()[0]} has attended {present_att} of {total_att} sessions with a {att_rate}% attendance rate across {len(modules)} module{'s' if len(modules) != 1 else ''} covered.",
        'classroom_stats':     classroom_stats,
        'modules':             modules,
        'session_log':         session_log,
        'topic_tags':          topic_tags,
        'tutor_comment':       tutor_comment,
    }

    return render(request, 'core/student_report.html', context)










# ─── Admin: Modules ───────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_module_create(request, course_pk):
    course = get_object_or_404(Course, pk=course_pk)
    form   = ModuleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        module        = form.save(commit=False)
        module.course = course
        module.save()
        messages.success(request, f"Module '{module.name}' added to {course.name}.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Add Module — {course.name}', 'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_module_edit(request, course_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=pk, course=course)
    form   = ModuleForm(request.POST or None, instance=module)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Module updated.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit Module — {module.name}', 'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_module_delete(request, course_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=pk, course=course)
    if request.method == 'POST':
        module.delete()
        messages.success(request, "Module deleted.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': module, 'back': 'admin_courses'
    })


# ─── Admin: Topics (now module-aware) ────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_topic_create(request, course_pk, module_pk):
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=module_pk, course=course)
    form   = TopicForm(course=course, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        topic        = form.save(commit=False)
        topic.course = course
        topic.module = module
        topic.save()
        messages.success(request, f"Topic added to {module.name}.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form,
        'title': f'Add Topic — {module.name}',
        'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_topic_edit(request, course_pk, module_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=module_pk, course=course)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    form   = TopicForm(course=course, data=request.POST or None, instance=topic)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Topic updated.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit Topic — {topic.title}', 'back_url': 'admin_courses'
    })


@login_required
@user_passes_test(is_admin)
def admin_topic_delete(request, course_pk, module_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    if request.method == 'POST':
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': topic, 'back': 'admin_courses'
    })


# ─── Tutor: Modules (mirrors admin) ──────────────────────────────────────────

@login_required
def tutor_module_create(request, course_pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    form   = ModuleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        module        = form.save(commit=False)
        module.course = course
        module.save()
        messages.success(request, f"Module '{module.name}' added.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Add Module — {course.name}', 'back_url': 'tutor_courses'
    })


@login_required
def tutor_module_edit(request, course_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=pk, course=course)
    form   = ModuleForm(request.POST or None, instance=module)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Module updated.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit Module — {module.name}', 'back_url': 'tutor_courses'
    })


@login_required
def tutor_module_delete(request, course_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=pk, course=course)
    if request.method == 'POST':
        module.delete()
        messages.success(request, "Module deleted.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': module, 'back': 'tutor_courses'
    })


@login_required
def tutor_topic_create(request, course_pk, module_pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=module_pk, course=course)
    form   = TopicForm(course=course, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        topic        = form.save(commit=False)
        topic.course = course
        topic.module = module
        topic.save()
        messages.success(request, f"Topic added to {module.name}.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Add Topic — {module.name}', 'back_url': 'tutor_courses'
    })


@login_required
def tutor_topic_edit(request, course_pk, module_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    module = get_object_or_404(Module, pk=module_pk, course=course)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    form   = TopicForm(course=course, data=request.POST or None, instance=topic)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Topic updated.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit Topic — {topic.title}', 'back_url': 'tutor_courses'
    })


@login_required
def tutor_topic_delete(request, course_pk, module_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    if request.method == 'POST':
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': topic, 'back': 'tutor_courses'
    })


# ─── API: topics by module (for session form JS) ─────────────────────────────

@login_required
def api_module_topics(request, module_pk):
    topics = Topic.objects.filter(module_id=module_pk).order_by('week', 'day').values(
        'id', 'title', 'week', 'day'
    )
    return JsonResponse({'topics': list(topics)})






@login_required
@user_passes_test(is_admin)
def admin_orphan_topic_delete(request, course_pk, pk):
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    if request.method == 'POST':
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect('admin_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': topic, 'back': 'admin_courses'
    })




@login_required
def tutor_orphan_topic_delete(request, course_pk, pk):
    tutor  = get_tutor_or_403(request)
    if not tutor: return redirect('login')
    course = get_object_or_404(Course, pk=course_pk)
    topic  = get_object_or_404(Topic, pk=pk, course=course)
    if request.method == 'POST':
        topic.delete()
        messages.success(request, "Topic deleted.")
        return redirect('tutor_course_detail', pk=course_pk)
    return render(request, 'core/confirm_delete.html', {
        'obj': topic, 'back': 'tutor_courses'
    })




# core/views.py — new admin views
@login_required
@user_passes_test(is_admin)
def admin_classroom_create(request):
    form = ClassroomForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        classroom = form.save()
        messages.success(request, f"Classroom '{classroom.name}' created. Join code: {classroom.join_code}")
        return redirect('admin_classroom_detail', pk=classroom.pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': 'Create Classroom', 'back_url': 'admin_classrooms'
    })

@login_required
@user_passes_test(is_admin)
def admin_classroom_edit(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    form = ClassroomForm(data=request.POST or None, instance=classroom)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Classroom updated.")
        return redirect('admin_classroom_detail', pk=pk)
    return render(request, 'core/form.html', {
        'form': form, 'title': f'Edit — {classroom.name}', 'back_url': 'admin_classrooms'
    })

@login_required
@user_passes_test(is_admin)
def admin_classroom_delete(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        classroom.delete()
        messages.success(request, "Classroom deleted.")
        return redirect('admin_classrooms')
    return render(request, 'core/confirm_delete.html', {'obj': classroom, 'back': 'admin_classrooms'})

@login_required
@user_passes_test(is_admin)
def admin_classroom_manage_students(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        student = get_object_or_404(Student, pk=request.POST.get('student_id'))
        if action == 'add':
            classroom.students.add(student)
            student.courses.add(classroom.course)
            if not student.tutor:
                student.tutor = classroom.tutor
                student.save()
            messages.success(request, f"{student.name} added to {classroom.name}.")
        elif action == 'remove':
            classroom.students.remove(student)
            messages.success(request, f"{student.name} removed from {classroom.name}.")
        return redirect('admin_classroom_detail', pk=pk)

    available = Student.objects.exclude(pk__in=classroom.students.values_list('pk', flat=True))
    return render(request, 'core/admin_classroom_manage_students.html', {
        'classroom': classroom, 'available_students': available,
    })