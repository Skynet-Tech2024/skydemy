from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Lesson, Subject, Course, Department, Exam, Certificate
from .models import LEVEL_CHOICES, CYCLE_CHOICES, CLASS_CHOICES

User = get_user_model()


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            'title',
            'level',
            'cycle',
            'class_level',
            'department',
            'subject',
            'course',
            'description',
            'pdf_file',
            'video_url',
            'video_file',
        ]
        widgets = {
            # level is handled separately in __init__
            'cycle': forms.Select(choices=CYCLE_CHOICES, attrs={'class': 'form-control'}),
            'class_level': forms.Select(choices=CLASS_CHOICES, attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'video_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Get teacher_level from kwargs (passed from view)
        teacher_level = kwargs.pop('teacher_level', None)
        super().__init__(*args, **kwargs)

        self.fields['subject'].queryset = Subject.objects.filter(status='approved')
        self.fields['course'].queryset = Course.objects.filter(status='approved')
        self.fields['department'].queryset = Department.objects.all()
        self.fields['class_level'].choices = CLASS_CHOICES

        # Level: visible but readonly, not required
        self.fields['level'].required = False
        if teacher_level:
            self.fields['level'].initial = teacher_level
        self.fields['level'].widget = forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'style': 'background-color: #f5f5f5; cursor: not-allowed;'
        })
        # Ensure the select choices are still available (though readonly will ignore them)

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get('level')
        cycle = cleaned_data.get('cycle')
        class_level = cleaned_data.get('class_level')
        department = cleaned_data.get('department')

        if level == 'secondary':
            if not cycle:
                self.add_error('cycle', 'Cycle is required for Secondary level.')
            if not class_level:
                self.add_error('class_level', 'Class is required for Secondary level.')
            if not department:
                self.add_error('department', 'Department is required for Secondary level.')
        return cleaned_data


class ExamForm(forms.ModelForm):
    """Form for teachers to create/edit exams."""
    class Meta:
        model = Exam
        fields = [
            'title',
            'exam_type',
            'subject',
            'course',
            'duration_minutes',
            'total_marks',
            'passing_score',
            'instructions',
            'exam_document',
            'marking_guide_document',
        ]
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 4}),
        }


# ===== ADMIN WIZARD FORMS =====

class ExamCreationForm(forms.ModelForm):
    """Form for admin to create an exam with optional file uploads."""
    exam_paper = forms.FileField(required=False, label='Exam Paper (PDF)')
    marking_guide = forms.FileField(required=False, label='Marking Guide (PDF)')

    class Meta:
        model = Exam
        fields = [
            'title',
            'exam_type',
            'course',
            'subject',
            'academic_session',
            'term',
            'level',
            'language',
            'exam_code',
            'duration_minutes',
            'total_marks',
            'passing_score',
            'number_of_questions',
            'instructions',
            'time_limit_minutes',
            'attempts_allowed',
            'question_order',
            'answer_order',
            'show_result_immediately',
            'show_correct_answers',
            'auto_submit',
            'late_submission',
            'visibility',
            'require_password',
            'exam_password',
            'require_safe_browser',
            'require_webcam',
            'randomize_questions',
            'grading_method',
            'negative_marking',
            'marks_per_question',
            'auto_grade_objective',
            'manual_review_required',
            'shuffle_questions',
            'shuffle_options',
            'fullscreen_mode',
            'disable_copy_paste',
            'browser_lock',
            'webcam_monitoring',
            'screen_recording',
            'tab_switching_detection',
            'ip_restriction',
            'notify_immediately',
            'notify_on_publish',
            'notify_before_deadline',
            'notify_after_grading',
            'teacher',
        ]
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 4}),
            'exam_password': forms.PasswordInput(render_value=True),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.filter(status='approved')
        self.fields['subject'].queryset = Subject.objects.filter(status='approved')
        self.fields['teacher'].queryset = User.objects.filter(profile__role='teacher')


class CertificateIssueForm(forms.Form):
    """Form for admin to issue a certificate."""
    ACHIEVEMENT_CHOICES = (
        ('lesson', 'Lesson Completion'),
        ('exam', 'Exam Pass'),
    )
    achievement_type = forms.ChoiceField(choices=ACHIEVEMENT_CHOICES, label='Achievement Type')
    user = forms.ModelChoiceField(queryset=User.objects.all(), label='User')
    lesson = forms.ModelChoiceField(queryset=Lesson.objects.filter(status='approved'), required=False, label='Lesson')
    exam = forms.ModelChoiceField(queryset=Exam.objects.filter(status='approved'), required=False, label='Exam')
    issue_date = forms.DateField(widget=forms.SelectDateWidget, label='Issue Date')
    expiry_date = forms.DateField(required=False, widget=forms.SelectDateWidget, label='Expiry Date (optional)')
    custom_message = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Custom Message')
    certificate_number = forms.CharField(max_length=50, required=False, label='Certificate Number (auto if blank)')

    def clean(self):
        cleaned_data = super().clean()
        achievement_type = cleaned_data.get('achievement_type')
        lesson = cleaned_data.get('lesson')
        exam = cleaned_data.get('exam')

        if achievement_type == 'lesson' and not lesson:
            self.add_error('lesson', 'Lesson is required when achievement type is Lesson Completion.')
        if achievement_type == 'exam' and not exam:
            self.add_error('exam', 'Exam is required when achievement type is Exam Pass.')
        return cleaned_data


class CourseCreationForm(forms.ModelForm):
    """Form for admin to create a course."""
    class Meta:
        model = Course
        fields = ['code', 'name', 'description', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }