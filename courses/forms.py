from django import forms
from django.core.exceptions import ValidationError
from .models import Lesson, Subject, Course, Department, Exam, Certificate
from .models import LEVEL_CHOICES, CYCLE_CHOICES, CLASS_CHOICES  # import the choices

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
            'level': forms.Select(choices=LEVEL_CHOICES),
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
        super().__init__(*args, **kwargs)
        # Dynamically set choices for subject and course (if needed)
        self.fields['subject'].queryset = Subject.objects.filter(status='approved')
        self.fields['course'].queryset = Course.objects.filter(status='approved')
        self.fields['department'].queryset = Department.objects.all()
        # Ensure class_level uses the full choice list
        self.fields['class_level'].choices = CLASS_CHOICES

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get('level')
        cycle = cleaned_data.get('cycle')
        class_level = cleaned_data.get('class_level')
        department = cleaned_data.get('department')

        # Validation for secondary level
        if level == 'secondary':
            if not cycle:
                self.add_error('cycle', 'Cycle is required for Secondary level.')
            if not class_level:
                self.add_error('class_level', 'Class is required for Secondary level.')
            if not department:
                self.add_error('department', 'Department is required for Secondary level.')
        return cleaned_data

    # You may add other custom validation as needed