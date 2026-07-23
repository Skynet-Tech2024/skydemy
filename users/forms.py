from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

# ===== STEP 1 FORM (only username, password, confirm) =====
class RegisterStep1Form(UserCreationForm):
    """Simplified registration form – Step 1: Create Account."""
    username = forms.CharField(
        max_length=150,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput,
        help_text="Enter the same password as above, for verification."
    )

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user


# ===== OLD FORM (kept for reference – NOT used in new flow) =====
class RegisterForm(UserCreationForm):
    """Original registration form – kept for backward compatibility."""
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