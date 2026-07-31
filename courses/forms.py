from django import forms
from .models import Lesson, Subject, Course, Exam, Certificate
from .constants import CYCLE_CHOICES, CLASS_CHOICES
from users.models import UserProfile
from .models import CYCLE_CHOICES, CLASS_CHOICES
from .models import Subject, Course, Lesson, Department
from core.constants import LEVEL_CHOICES
from django.conf import settings
from django.contrib.auth import get_user_model
import datetime
import random



class LessonForm(forms.ModelForm):
    # Add the new fields
    cycle = forms.ChoiceField(
        choices=[('', '-- Select Cycle --')] + list(CYCLE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_cycle'})
    )
    class_level = forms.ChoiceField(
        choices=[('', '-- Select Class --')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_class_level'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all().order_by('name'),
        required=False,
        empty_label="-- Select Department --",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_department'})
    )

    class Meta:
        model = Lesson
        fields = [
            'title', 'level', 'subject', 'course',
            'cycle', 'class_level', 'department',
            'description', 'pdf_file', 'video_url', 'video_file'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control', 'id': 'id_level'}),
            'subject': forms.Select(attrs={'class': 'form-control', 'id': 'id_subject'}),
            'course': forms.Select(attrs={'class': 'form-control', 'id': 'id_course'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial choices for class_level (empty)
        self.fields['class_level'].choices = [('', '-- Select Class --')]
        # If the instance has a cycle, update class_level choices
        if self.instance and self.instance.pk and self.instance.cycle:
            self.fields['class_level'].choices = self.get_class_choices(self.instance.cycle)

    def get_class_choices(self, cycle):
        """Return class choices based on cycle."""
        if cycle == 'first':
            return [('', '-- Select Class --')] + [
                ('form3', 'Form 3'),
                ('form4', 'Form 4'),
                ('form5', 'Form 5'),
            ]
        elif cycle == 'second':
            return [('', '-- Select Class --')] + [
                ('lower_sixth', 'Lower Sixth'),
                ('upper_sixth', 'Upper Sixth'),
            ]
        return [('', '-- Select Class --')]

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get('level')
        cycle = cleaned_data.get('cycle')
        class_level = cleaned_data.get('class_level')
        department = cleaned_data.get('department')

        # If level is secondary, require cycle, class_level, and department
        if level == 'secondary':
            if not cycle:
                self.add_error('cycle', 'Cycle is required for Secondary level.')
            if not class_level:
                self.add_error('class_level', 'Class is required for Secondary level.')
            if not department:
                self.add_error('department', 'Department is required for Secondary level.')
        else:
            # If not secondary, clear these fields (they are not needed)
            cleaned_data['cycle'] = None
            cleaned_data['class_level'] = None
            cleaned_data['department'] = None

        return cleaned_data



class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            'title', 'exam_type', 'course', 'subject',
            'academic_session', 'term', 'level', 'language',
            'duration_minutes', 'total_marks', 'passing_score',
            'number_of_questions', 'instructions',
            'time_limit_minutes', 'attempts_allowed',
            'question_order', 'answer_order',
            'show_result_immediately', 'show_correct_answers',
            'auto_submit', 'late_submission',
            'visibility', 'require_password', 'exam_password',
            'require_safe_browser', 'require_webcam', 'randomize_questions',
            'grading_method', 'negative_marking', 'marks_per_question',
            'auto_grade_objective', 'manual_review_required',
            'shuffle_questions', 'shuffle_options', 'fullscreen_mode',
            'disable_copy_paste', 'browser_lock', 'webcam_monitoring',
            'screen_recording', 'tab_switching_detection', 'ip_restriction',
            'notify_immediately', 'notify_on_publish',
            'notify_before_deadline', 'notify_after_grading',
            'status', 'admin_notes',
            'exam_document', 'marking_guide_document',
        ]
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 4}),
            'admin_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional_fields = [
            'course', 'subject', 'academic_session', 'term', 'level', 'language',
            'time_limit_minutes', 'attempts_allowed', 'exam_password',
            'admin_notes', 'exam_document', 'marking_guide_document',
            'instructions'
        ]
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False


# ===== Exam Creation Wizard Form =====
class ExamCreationForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.Select(attrs={'class': 'searchable-dropdown'}),
        required=True
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=forms.Select(attrs={'class': 'searchable-dropdown'}),
        required=False
    )
    exam_paper = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'file-upload', 'accept': '.pdf,.docx'})
    )
    marking_guide = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'file-upload', 'accept': '.pdf,.docx'})
    )
    title = forms.CharField(max_length=200)
    level = forms.ChoiceField(choices=LEVEL_CHOICES)
    category = forms.ChoiceField(choices=[
        ('midterm', 'Mid-Term Examination'),
        ('endterm', 'End-of-Term Examination'),
        ('mock', 'Mock Examination'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz'),
        ('continuous', 'Continuous Assessment'),
        ('practice', 'Practice Test'),
        ('final', 'Final Examination'),
        ('certification', 'Certification Exam')
    ])
    description = forms.CharField(widget=forms.Textarea, required=False)
    time_limit = forms.ChoiceField(choices=[
        (30, '30 minutes'),
        (60, '60 minutes'),
        (90, '90 minutes'),
        (120, '120 minutes'),
        ('custom', 'Custom')
    ])
    passing_score = forms.IntegerField(min_value=0, max_value=100)
    total_marks = forms.IntegerField(min_value=1)
    attempts_allowed = forms.ChoiceField(choices=[
        (1, '1'),
        (2, '2'),
        (3, '3'),
        (0, 'Unlimited')
    ])
    start_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    end_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    randomize_questions = forms.BooleanField(required=False)
    shuffle_options = forms.BooleanField(required=False)
    auto_grade = forms.BooleanField(required=False)
    show_results = forms.BooleanField(required=False)
    allow_review = forms.BooleanField(required=False)
    certificate_eligible = forms.BooleanField(required=False)
    anti_cheating = forms.BooleanField(required=False)

    class Meta:
        model = Exam
        fields = [
            'title', 'level', 'category', 'subject', 'course', 'description',
            'time_limit', 'passing_score', 'total_marks', 'attempts_allowed',
            'start_date', 'end_date', 'randomize_questions', 'shuffle_options',
            'auto_grade', 'show_results', 'allow_review', 'certificate_eligible',
            'anti_cheating'
        ]

    def clean(self):
        return self.cleaned_data


# ===== CERTIFICATE ISSUANCE WIZARD FORM =====
class CertificateIssueForm(forms.ModelForm):
    user = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        widget=forms.Select(attrs={'class': 'searchable-dropdown'}),
        required=True,
        label="Recipient (Student)"
    )
    achievement_type = forms.ChoiceField(
        choices=[('lesson', 'Lesson'), ('exam', 'Exam')],
        widget=forms.RadioSelect,
        initial='lesson',
        label="Achievement Type"
    )
    lesson = forms.ModelChoiceField(
        queryset=Lesson.objects.filter(status='approved'),
        required=False,
        widget=forms.Select(attrs={'class': 'searchable-dropdown'}),
        label="Lesson"
    )
    exam = forms.ModelChoiceField(
        queryset=Exam.objects.filter(status='approved'),
        required=False,
        widget=forms.Select(attrs={'class': 'searchable-dropdown'}),
        label="Exam"
    )
    issue_date = forms.DateField(
        initial=datetime.date.today,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Issue Date"
    )
    expiry_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Expiry Date (optional)"
    )
    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        label="Custom Message (optional)"
    )
    certificate_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        label="Certificate Number (auto‑generated)"
    )

    class Meta:
        model = Certificate
        fields = ['user', 'lesson', 'certificate_number', 'issue_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = get_user_model().objects.filter(profile__role='learner')
        if not self.instance.pk:
            self.fields['certificate_number'].initial = self.generate_certificate_number()

    def generate_certificate_number(self):
        return f"CERT-{datetime.datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

    def clean(self):
        cleaned_data = super().clean()
        achievement_type = cleaned_data.get('achievement_type')
        lesson = cleaned_data.get('lesson')
        exam = cleaned_data.get('exam')
        if achievement_type == 'lesson' and not lesson:
            self.add_error('lesson', 'Please select a lesson.')
        elif achievement_type == 'exam' and not exam:
            self.add_error('exam', 'Please select an exam.')
        return cleaned_data


# ===== COURSE CREATION WIZARD FORM =====
class CourseCreationForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['code', 'name', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = True
        self.fields['name'].required = True
        self.fields['description'].required = False
        self.fields['status'].required = False