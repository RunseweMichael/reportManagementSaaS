from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Tutor ─────────────────────────────────────────────────────────────────
    path('tutor/dashboard/', views.tutor_dashboard, name='tutor_dashboard'),

    # Students
    path('tutor/students/',                     views.tutor_students,        name='tutor_students'),
    path('tutor/students/<int:pk>/',            views.tutor_student_detail,  name='tutor_student_detail'),
    path('tutor/students/<int:pk>/edit/',       views.tutor_student_edit,    name='tutor_student_edit'),
    path('tutor/students/<int:pk>/delete/',     views.tutor_student_delete,  name='tutor_student_delete'),

    # Classrooms
    path('tutor/classrooms/',                                views.tutor_classrooms,                     name='tutor_classrooms'),
    path('tutor/classrooms/<int:pk>/',                       views.tutor_classroom_detail,               name='tutor_classroom_detail'),
    path('tutor/classrooms/<int:pk>/sessions/create/',       views.tutor_classroom_session_create,       name='tutor_classroom_session_create'),
    path('tutor/classrooms/<int:pk>/sessions/<int:spk>/attendance/', views.tutor_classroom_session_attendance, name='tutor_classroom_session_attendance'),

    # Standalone sessions
    path('tutor/classes/',               views.tutor_classes,      name='tutor_classes'),
    path('tutor/classes/create/',        views.tutor_class_create, name='tutor_class_create'),
    path('tutor/classes/<int:pk>/',      views.tutor_class_detail, name='tutor_class_detail'),
    path('tutor/classes/<int:pk>/edit/', views.tutor_class_edit,   name='tutor_class_edit'),
    path('tutor/classes/<int:pk>/delete/', views.tutor_class_delete, name='tutor_class_delete'),
    path('tutor/classes/<int:class_pk>/attendance/', views.take_attendance, name='take_attendance'),

    
    # Tutor: Courses + Topics
    path('tutor/courses/',                                          views.tutor_courses,       name='tutor_courses'),
    path('tutor/courses/create/',                                   views.tutor_course_create, name='tutor_course_create'),
    path('tutor/courses/<int:pk>/',                                 views.tutor_course_detail, name='tutor_course_detail'),
    path('tutor/courses/<int:pk>/edit/',                            views.tutor_course_edit,   name='tutor_course_edit'),
    path('tutor/courses/<int:pk>/delete/',                          views.tutor_course_delete, name='tutor_course_delete'),
    path('tutor/courses/<int:course_pk>/topics/create/',            views.tutor_topic_create,  name='tutor_topic_create'),
    path('tutor/courses/<int:course_pk>/topics/<int:pk>/edit/',     views.tutor_topic_edit,    name='tutor_topic_edit'),
    path('tutor/courses/<int:course_pk>/topics/<int:pk>/delete/',   views.tutor_topic_delete,  name='tutor_topic_delete'),


    path('tutor/change-password/', views.tutor_change_password, name='tutor_change_password'),


    # Timetable
    path('tutor/timetable/',                   views.tutor_timetable,        name='tutor_timetable'),
    path('tutor/timetable/create/',            views.tutor_timetable_create, name='tutor_timetable_create'),
    path('tutor/timetable/<int:pk>/edit/',     views.tutor_timetable_edit,   name='tutor_timetable_edit'),
    path('tutor/timetable/<int:pk>/delete/',   views.tutor_timetable_delete, name='tutor_timetable_delete'),

    # Reports
    path('tutor/reports/',               views.tutor_reports,       name='tutor_reports'),
    path('tutor/reports/create/',        views.tutor_report_create, name='tutor_report_create'),
    path('tutor/reports/<int:pk>/edit/', views.tutor_report_edit,   name='tutor_report_edit'),

    # ── API (JSON endpoints) ──────────────────────────────────────────────────
    path('api/courses/<int:course_pk>/topics/',   views.api_course_topics,    name='api_course_topics'),
    path('api/tutors/<int:tutor_pk>/classrooms/', views.api_tutor_classrooms, name='api_tutor_classrooms'),

    # ── Admin ─────────────────────────────────────────────────────────────────
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/students/<int:pk>/report/', views.admin_student_report, name='admin_student_report'),

    # Tutors
    path('admin-panel/tutors/',                  views.admin_tutors,        name='admin_tutors'),
    path('admin-panel/tutors/create/',           views.admin_tutor_create,  name='admin_tutor_create'),
    path('admin-panel/tutors/<int:pk>/',         views.admin_tutor_detail,  name='admin_tutor_detail'),
    path('admin-panel/tutors/<int:pk>/edit/',    views.admin_tutor_edit,    name='admin_tutor_edit'),
    path('admin-panel/tutors/<int:pk>/delete/',  views.admin_tutor_delete,  name='admin_tutor_delete'),
    path('admin-panel/tutors/<int:pk>/reset-password/', views.admin_tutor_reset_password, name='admin_tutor_reset_password'),
    path('register/', views.tutor_register, name='tutor_register'),
    path('admin-panel/tutors/<int:pk>/approve/', views.admin_tutor_approve, name='admin_tutor_approve'),
    path('admin-panel/change-password/', views.admin_change_password, name='admin_change_password'),

    # Students
    path('admin-panel/students/',                views.admin_students,        name='admin_students'),
    path('admin-panel/students/<int:pk>/',       views.admin_student_detail,  name='admin_student_detail'),
    path('admin-panel/students/<int:pk>/edit/',  views.admin_student_edit,    name='admin_student_edit'),
    path('admin-panel/students/<int:pk>/delete/', views.admin_student_delete, name='admin_student_delete'),
    path('admin-panel/students/<int:pk>/assign/', views.admin_student_assign, name='admin_student_assign'),
    path('admin-panel/students/sync/', views.admin_sync_students, name='admin_sync_students'),
    path('admin-panel/classrooms/create/',                  views.admin_classroom_create,           name='admin_classroom_create'),
    path('admin-panel/classrooms/<int:pk>/edit/',           views.admin_classroom_edit,             name='admin_classroom_edit'),
    path('admin-panel/classrooms/<int:pk>/delete/',         views.admin_classroom_delete,           name='admin_classroom_delete'),
    path('admin-panel/classrooms/<int:pk>/manage-students/',views.admin_classroom_manage_students,  name='admin_classroom_manage_students'),



    # Classrooms
    path('admin-panel/classrooms/',          views.admin_classrooms,        name='admin_classrooms'),
    path('admin-panel/classrooms/<int:pk>/', views.admin_classroom_detail,  name='admin_classroom_detail'),

    # Timetable
    path('admin-panel/timetable/',                   views.admin_timetable,        name='admin_timetable'),
    path('admin-panel/timetable/create/',            views.admin_timetable_create, name='admin_timetable_create'),
    path('admin-panel/timetable/<int:pk>/edit/',     views.admin_timetable_edit,   name='admin_timetable_edit'),
    path('admin-panel/timetable/<int:pk>/delete/',   views.admin_timetable_delete, name='admin_timetable_delete'),

    # Reports
    path('admin-panel/reports/',           views.admin_reports,       name='admin_reports'),
    path('admin-panel/reports/<int:pk>/',  views.admin_report_detail, name='admin_report_detail'),

    # Courses + Topics
    path('admin-panel/courses/',                 views.admin_courses,       name='admin_courses'),
    path('admin-panel/courses/create/',          views.admin_course_create, name='admin_course_create'),
    path('admin-panel/courses/<int:pk>/',        views.admin_course_detail, name='admin_course_detail'),
    path('admin-panel/courses/<int:pk>/edit/',   views.admin_course_edit,   name='admin_course_edit'),
    path('admin-panel/courses/<int:pk>/delete/', views.admin_course_delete, name='admin_course_delete'),
    path('admin-panel/courses/<int:course_pk>/topics/create/',             views.admin_topic_create, name='admin_topic_create'),
    path('admin-panel/courses/<int:course_pk>/topics/<int:pk>/edit/',      views.admin_topic_edit,   name='admin_topic_edit'),
    path('admin-panel/courses/<int:course_pk>/topics/<int:pk>/delete/',    views.admin_topic_delete, name='admin_topic_delete'),
    path('admin-panel/courses/sync/', views.admin_sync_courses, name='admin_sync_courses'),


    # Admin: Modules
    path('admin-panel/courses/<int:course_pk>/modules/create/',           views.admin_module_create, name='admin_module_create'),
    path('admin-panel/courses/<int:course_pk>/modules/<int:pk>/edit/',    views.admin_module_edit,   name='admin_module_edit'),
    path('admin-panel/courses/<int:course_pk>/modules/<int:pk>/delete/',  views.admin_module_delete, name='admin_module_delete'),

    # Admin: Topics now nested under module
    path('admin-panel/courses/<int:course_pk>/modules/<int:module_pk>/topics/create/',          views.admin_topic_create, name='admin_topic_create'),
    path('admin-panel/courses/<int:course_pk>/modules/<int:module_pk>/topics/<int:pk>/edit/',   views.admin_topic_edit,   name='admin_topic_edit'),
    path('admin-panel/courses/<int:course_pk>/modules/<int:module_pk>/topics/<int:pk>/delete/', views.admin_topic_delete, name='admin_topic_delete'),

    # Tutor: Modules
    path('tutor/courses/<int:course_pk>/modules/create/',           views.tutor_module_create, name='tutor_module_create'),
    path('tutor/courses/<int:course_pk>/modules/<int:pk>/edit/',    views.tutor_module_edit,   name='tutor_module_edit'),
    path('tutor/courses/<int:course_pk>/modules/<int:pk>/delete/',  views.tutor_module_delete, name='tutor_module_delete'),
 
    # Tutor: Topics nested under module
    path('tutor/courses/<int:course_pk>/modules/<int:module_pk>/topics/create/',          views.tutor_topic_create, name='tutor_topic_create'),
    path('tutor/courses/<int:course_pk>/modules/<int:module_pk>/topics/<int:pk>/edit/',   views.tutor_topic_edit,   name='tutor_topic_edit'),
    path('tutor/courses/<int:course_pk>/modules/<int:module_pk>/topics/<int:pk>/delete/', views.tutor_topic_delete, name='tutor_topic_delete'),
    path('api/modules/<int:module_pk>/topics/', views.api_module_topics, name='api_module_topics'),

    path('tutor/courses/<int:course_pk>/topics/<int:pk>/delete/', views.tutor_orphan_topic_delete, name='tutor_orphan_topic_delete'),
]
