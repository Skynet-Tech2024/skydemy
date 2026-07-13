from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    level = forms.ChoiceField(choices=UserProfile.LEVEL_CHOICES, required=False)
    avatar = forms.ImageField(required=False, label="Profile Picture", help_text="Upload a profile picture")
    captcha = CaptchaField(label="Enter the text shown below")  # <-- Added captcha field
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role', 'level', 'avatar', 'captcha']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create UserProfile with pending verification
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                level=self.cleaned_data['level'] if self.cleaned_data['level'] else None,
                verification_status='pending',  # New users require admin approval
                avatar=self.cleaned_data.get('avatar')  # Save the uploaded avatar
            )
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'level']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }