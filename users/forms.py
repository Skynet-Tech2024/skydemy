from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Level
from core.constants import LEVEL_CHOICES


# ===== STEP 1: ACCOUNT CREATION =====
class RegisterStep1Form(UserCreationForm):
    full_name = forms.CharField(
        max_length=200,
        label="Full Names",
        help_text="Enter your full name (e.g., CHE KENNETH).",
    )
    username = forms.CharField(
        max_length=150,
        label="Choose Username",
        help_text="This will be your login name. Must be unique.",
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        help_text="Enter your password (any length, any characters).",
        validators=[],
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above.",
        validators=[],
    )

    class Meta:
        model = User
        fields = ['full_name', 'username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].validators = []
        self.fields['password1'].validators = []
        self.fields['password2'].validators = []

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        return username.strip()

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.full_name = self.cleaned_data['full_name']
            if created:
                profile.role = 'learner'
                profile.verification_status = 'pending'
            profile.save()
        return user


# ===== PROFILE UPDATE FORM (used for Step 2: role + levels) =====
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'levels', 'bio', 'avatar']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'levels': forms.CheckboxSelectMultiple(),
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }
        help_texts = {
            'levels': 'Select all levels that apply to you (teachers can select multiple).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['levels'].queryset = Level.objects.all()
        self.fields['levels'].required = True