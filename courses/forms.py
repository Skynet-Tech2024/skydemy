from django import forms
from .models import Lesson, Subject, Course, Exam, Certificate
from core.constants import LEVEL_CHOICES
from django.conf import settings
import datetime
import random


class LessonForm(forms.ModelForm):
    # Add a field for creating a new subject on the fly
    new_subject_name = forms.CharField(
        max_length=100, 
        required=False,
        help_text="If subject doesn't exist, enter a new subject name here and it will be created automatically."
    )
    new_subject_level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        required=False,
        help_text="Select the level for the new subject"
    )
    
    class Meta:
        model = Lesson
        fields = ['title', 'description', 'level', 'subject', 'course', 'pdf_file', 'video_file', 'video_url', 'new_subject_name', 'new_subject_level']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subject'].required = False
        self.fields['course'].required = False
        self.fields['pdf_file'].required = False
        self.fields['video_file'].required = False
        self.fields['video_url'].required = False
        
        # Filter subjects to show only those matching the selected level
        if 'level' in self.data:
            level = self.data.get('level')
            if level:
                self.fields['subject'].queryset = Subject.objects.filter(level=level)
    
    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get('level')
        subject = cleaned_data.get('subject')
        new_subject_name = cleaned_data.get('new_subject_name')
        new_subject_level = cleaned_data.get('new_subject_level')
        
        # If user wants to create a new subject
        if new_subject_name and new_subject_level:
            # Check if subject already exists
            existing_subject = Subject.objects.filter(name__iexact=new_subject_name, level=new_subject_level).first()
            if existing_subject:
                cleaned_data['subject'] = existing_subject
            else:
                # Create new subject
                new_subject = Subject.objects.create(
                    name=new_subject_name,
                    level=new_subject_level,
                    description=f"Auto-created from lesson upload"
                )
                cleaned_data['subject'] = new_subject
        
        # Validation: subject required for primary/secondary
        if level in ['primary', 'secondary'] and not cleaned_data.get('subject'):
            raise forms.ValidationError('Please select an existing subject or create a new one by filling in "New Subject Name" and "New Subject Level".')
        
        # Validation: course required for university
        if level == 'university' and not cleaned_data.get('course'):
            raise forms.ValidationError('Please select a course for university level.')
        
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
        # Make optional fields not required
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
        queryset=settings.AUTH_USER_MODEL.objects.filter(profile__role='learner'),
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