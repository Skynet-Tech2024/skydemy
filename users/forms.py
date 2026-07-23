from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

# ===== STEP 1 FORM – Full Names (no restrictions), Password (no restrictions) =====
class RegisterStep1Form(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        label="Full Names",
        help_text="Enter your full name.",
        validators=[],  # Remove all validators – any characters allowed
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        help_text="Enter your password (any length, any characters).",
        validators=[],  # No validators – even 1 character is allowed
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above.",
        validators=[],
    )

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data['username']
        # Only strip leading/trailing spaces; keep everything else
        return username.strip()

    def clean_password2(self):
        """Skip all Django password validators – accept anything."""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        # DO NOT call validate_password – this bypasses all validators
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


# ===== OLD FORM (kept for reference – NOT used in new flow) =====
class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        help_text="Optional. Used for password recovery and notifications."
    )
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, required=True)
    level = forms.ChoiceField(choices=UserProfile.LEVEL_CHOICES, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role', 'level']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = user.profile
            profile.role = self.cleaned_data['role']
            profile.level = self.cleaned_data['level']
            profile.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'bio',
            'avatar',
            'level',
            'date_of_birth',
            'address',
        ]
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'level': 'Your education level (required)',
            'date_of_birth': 'Your date of birth',
            'address': 'Your physical address',
        }