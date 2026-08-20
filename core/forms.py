from django import forms
from .models import (
    Tutor, Student, Course, Topic, Class, Module,
    TimetableEntry, Attendance, WeeklyReport, Classroom
)


class TutorLoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


# ─── Tutor management ─────────────────────────────────────────────────────────

from django import forms
from django.contrib.auth.models import User
from .models import Tutor

class TutorForm(forms.ModelForm):
    # ── User account fields ───────────────────────────────────────────────
    username   = forms.CharField(
        max_length=150,
        help_text="Used to log in to the tutor portal.",
    )
    first_name = forms.CharField(max_length=150, required=False)
    last_name  = forms.CharField(max_length=150, required=False)
    email      = forms.EmailField(required=False)
    specialization = forms.CharField(max_length=150, required=False)

    class Meta:
        model  = Tutor
        # list only the Tutor model's own fields here — NOT username/first_name/etc.
        fields = ['phone', 'mode', 'active']   # adjust to your actual Tutor fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        # When editing an existing tutor, pre-fill from their User
        if instance and hasattr(instance, 'user'):
            self.fields['username'].initial   = instance.user.username
            self.fields['first_name'].initial = instance.user.first_name
            self.fields['last_name'].initial  = instance.user.last_name
            self.fields['email'].initial      = instance.user.email

    def clean_username(self):
        username = self.cleaned_data['username']
        instance = self.instance
        qs = User.objects.filter(username=username)
        # On edit, exclude the tutor's own user from the uniqueness check
        if instance and instance.pk and hasattr(instance, 'user'):
            qs = qs.exclude(pk=instance.user.pk)
        if qs.exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username


# ─── Student forms ────────────────────────────────────────────────────────────

class TutorAddStudentForm(forms.ModelForm):
    """
    Tutor adds a student and immediately places them in a classroom.
    Classroom queryset is filtered to this tutor's classrooms in __init__.
    Selecting a classroom auto-sets the course.
    """
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.none(),
        required=True,
        empty_label="— Select a classroom —",
        label="Classroom",
        help_text="The student will be enrolled in the course linked to this classroom."
    )

    class Meta:
        model  = Student
        fields = ['name', 'email', 'phone', 'mode', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'mode':  forms.Select(),
        }

    def __init__(self, tutor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tutor:
            self.tutor = tutor
            self.fields['classroom'].queryset = Classroom.objects.filter(
                tutor=tutor, status='active'
            ).select_related('course')
            # Show course name next to classroom name in dropdown
            self.fields['classroom'].label_from_instance = lambda obj: f"{obj.name} ({obj.course.name})"

    def save(self, commit=True):
        student          = super().save(commit=False)
        student.tutor    = self.tutor
        classroom        = self.cleaned_data['classroom']
        student.active   = True
        if commit:
            student.save()
            student.courses.add(classroom.course)
            classroom.students.add(student)
        return student


class AdminAddStudentForm(forms.ModelForm):
    """Admin version — can pick any tutor and any classroom."""
    tutor = forms.ModelChoiceField(
        queryset=Tutor.objects.filter(active=True),
        required=True,
        empty_label="— Select a tutor —",
    )
    classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.filter(status='active').select_related('course', 'tutor'),
        required=True,
        empty_label="— Select a classroom —",
        help_text="Student will be enrolled in this classroom and its course."
    )

    class Meta:
        model  = Student
        fields = ['name', 'email', 'phone', 'mode', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'mode':  forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['classroom'].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.course.name}) — {obj.tutor.name}"
        )

    def save(self, commit=True):
        student        = super().save(commit=False)
        student.tutor  = self.cleaned_data['tutor']
        classroom      = self.cleaned_data['classroom']
        student.active = True
        if commit:
            student.save()
            student.courses.add(classroom.course)
            classroom.students.add(student)
        return student


class StudentEditForm(forms.ModelForm):
    """Edit basic student info — tutor can also move student to different classroom."""
    class Meta:
        model  = Student
        fields = ['name', 'email', 'phone', 'mode', 'active', 'current_week', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'mode':  forms.Select(),
        }


class AdminStudentEditForm(forms.ModelForm):
    """Admin can also reassign tutor."""
    class Meta:
        model  = Student
        fields = ['name', 'email', 'phone', 'tutor', 'mode', 'active', 'current_week', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'mode':  forms.Select(),
        }


# ─── Course / Topic ───────────────────────────────────────────────────────────

class CourseForm(forms.ModelForm):
    class Meta:
        model  = Course
        fields = ['name', 'code', 'description', 'duration_weeks']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class ModuleForm(forms.ModelForm):
    class Meta:
        model  = Module
        fields = ['name', 'order', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}


class TopicForm(forms.ModelForm):
    class Meta:
        model  = Topic
        fields = ['module', 'week', 'day', 'title', 'details']
        widgets = {'details': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, course=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields['module'].queryset = Module.objects.filter(course=course)
        else:
            self.fields['module'].queryset = Module.objects.none()
        self.fields['module'].empty_label = "— No module —"
        self.fields['module'].required = False


# ─── Class / Session ──────────────────────────────────────────────────────────

class ClassroomSessionForm(forms.ModelForm):
    """Post a session into a classroom — course/tutor set automatically."""
    class Meta:
        model  = Class
        fields = ['topic', 'date', 'start_time', 'end_time', 'description', 'comment']
        widgets = {
            'date':        forms.DateInput(attrs={'type': 'date'}),
            'start_time':  forms.TimeInput(attrs={'type': 'time'}),
            'end_time':    forms.TimeInput(attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'comment':     forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, classroom=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if classroom:
            self.fields['topic'].queryset    = Topic.objects.filter(
                course=classroom.course
            ).order_by('week', 'day')
            self.fields['topic'].empty_label = "— Select topic —"


class TutorClassForm(forms.ModelForm):
    """Standalone class (not inside a classroom) — scoped to tutor."""
    class Meta:
        model  = Class
        fields = ['course', 'topic', 'date', 'start_time', 'end_time',
                  'students', 'description', 'comment']
        widgets = {
            'course':      forms.Select(attrs={'id': 'id_course'}),
            'topic':       forms.Select(attrs={'id': 'id_topic'}),
            'date':        forms.DateInput(attrs={'type': 'date'}),
            'start_time':  forms.TimeInput(attrs={'type': 'time'}),
            'end_time':    forms.TimeInput(attrs={'type': 'time'}),
            'students':    forms.CheckboxSelectMultiple(),
            'description': forms.Textarea(attrs={'rows': 2}),
            'comment':     forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, tutor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tutor:
            self.fields['students'].queryset = Student.objects.filter(tutor=tutor)
            self.fields['course'].queryset   = Course.objects.filter(
                students__tutor=tutor
            ).distinct()

        # Resolve course_pk from POST data, or from existing instance (edit)
        course_pk = (
            self.data.get('course')                                          # POST submission
            or (self.instance.pk and self.instance.course_id or None)        # editing existing
        )

        if course_pk:
            self.fields['topic'].queryset = Topic.objects.filter(
                course_id=course_pk
            ).order_by('week', 'day')
        else:
            self.fields['topic'].queryset    = Topic.objects.none()
            self.fields['topic'].empty_label = "— Select a course first —"


# ─── Timetable ────────────────────────────────────────────────────────────────

class TimetableEntryForm(forms.ModelForm):
    class Meta:
        model  = TimetableEntry
        fields = ['tutor', 'course', 'day_of_week', 'start_time', 'end_time', 'subject', 'notes', 'students','location']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time':   forms.TimeInput(attrs={'type': 'time'}),
            'students':   forms.CheckboxSelectMultiple(),
            'notes':      forms.Textarea(attrs={'rows': 2}),
            'location': forms.Select(attrs={'id': 'id_location'}),
        }
    


class TutorTimetableEntryForm(forms.ModelForm):
    class Meta:
        model  = TimetableEntry
        fields = ['course', 'day_of_week', 'start_time', 'end_time','location', 'subject', 'notes', 'students']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time':   forms.TimeInput(attrs={'type': 'time'}),
            'students':   forms.CheckboxSelectMultiple(),
            'notes':      forms.Textarea(attrs={'rows': 2}),
            'location': forms.Select(attrs={'id': 'id_location'}),
        }

    def __init__(self, tutor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tutor:
            self.fields['students'].queryset = Student.objects.filter(tutor=tutor)
        
        # If tutor is online, hide location entirely
        if tutor and tutor.mode == 'online':
            self.fields['location'].widget = forms.HiddenInput()
            self.fields['location'].required = False
        else:
            self.fields['location'].required = True


# ─── Classroom ────────────────────────────────────────────────────────────────

class ClassroomForm(forms.ModelForm):
    class Meta:
        model  = Classroom
        fields = ['name', 'course', 'status', 'start_date', 'end_date', 'description']
        widgets = {
            'start_date':  forms.DateInput(attrs={'type': 'date'}),
            'end_date':    forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, tutor=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if tutor:
            self.fields['course'].queryset = Course.objects.all()


# ─── Reports ──────────────────────────────────────────────────────────────────

class WeeklyReportForm(forms.ModelForm):
    class Meta:
        model  = WeeklyReport
        fields = ['topics_covered', 'challenges', 'plan_next_week']
        widgets = {
            'topics_covered': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Topics covered this week...'}),
            'challenges':     forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any challenges or blockers...'}),
            'plan_next_week': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Plan for next week...'}),
        }


class AdminFeedbackForm(forms.ModelForm):
    class Meta:
        model  = WeeklyReport
        fields = ['admin_feedback', 'status']
        widgets = {'admin_feedback': forms.Textarea(attrs={'rows': 4})}



from django.contrib.auth.models import User

class TutorRegistrationForm(forms.Form):
    # Account fields
    first_name = forms.CharField(max_length=150)
    last_name  = forms.CharField(max_length=150)
    username   = forms.CharField(max_length=150)
    email      = forms.EmailField()
    password   = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    # Tutor profile fields
    phone          = forms.CharField(max_length=20, required=False)
    specialization = forms.CharField(max_length=255, required=False)
    mode           = forms.ChoiceField(choices=Tutor.MODE_CHOICES)
    bio            = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned