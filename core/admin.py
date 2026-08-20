from django.contrib import admin
from .models import (
    Course, Topic, Tutor, Student, Class,
    Attendance, TimetableEntry, WeeklyReport, Classroom
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'duration_weeks', 'created_at']
    search_fields = ['name', 'code']


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display  = ['title', 'course', 'week', 'day']
    list_filter   = ['course', 'week']
    search_fields = ['title', 'course__name']


@admin.register(Tutor)
class TutorAdmin(admin.ModelAdmin):
    list_display  = ['name', 'mode', 'specialization', 'active', 'created_at']
    list_filter   = ['mode', 'active']
    search_fields = ['name']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display   = ['name', 'tutor', 'mode', 'active', 'current_week', 'enrolled_at']
    list_filter    = ['mode', 'active', 'tutor']
    search_fields  = ['name', 'email']
    filter_horizontal = ['courses']
    raw_id_fields  = ['user']


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display      = ['name', 'course', 'tutor', 'status', 'join_code', 'start_date', 'created_at']
    list_filter       = ['status', 'tutor__mode', 'course']
    search_fields     = ['name', 'join_code', 'tutor__name']
    filter_horizontal = ['students']
    readonly_fields   = ['join_code', 'created_at']


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display      = ['course', 'tutor', 'classroom', 'topic', 'date', 'code', 'created_at']
    list_filter       = ['course', 'tutor', 'date']
    search_fields     = ['course__name', 'tutor__name', 'code']
    filter_horizontal = ['students']
    date_hierarchy    = 'date'
    readonly_fields   = ['code', 'created_at']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display  = ['student', 'class_instance', 'date', 'attendance_status']
    list_filter   = ['attendance_status', 'date']
    search_fields = ['student__name']
    date_hierarchy = 'date'


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display      = ['tutor', 'course', 'get_day_of_week_display', 'start_time', 'end_time', 'subject']
    list_filter       = ['tutor', 'day_of_week']
    filter_horizontal = ['students']


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display   = ['tutor', 'week_start', 'week_end', 'classes_held', 'students_attended', 'status']
    list_filter    = ['status', 'tutor']
    date_hierarchy = 'week_start'
    readonly_fields = ['created_at', 'updated_at']
