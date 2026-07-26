from django import forms
from .models import Lesson, Subject, Course, Exam

class LessonForm(forms.ModelForm):
    # Add a field for creating a new subject on the fly
    new_subject_name = forms.CharField(
        max_length=100, 
        required=False,
        help_text="If subject doesn't exist, enter a new subject name here and it will be created automatically."
    )
    new_subject_level = forms.ChoiceField(
        choices=Subject.LEVEL_CHOICES,
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
            # File upload fields (if you want them in the form)
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