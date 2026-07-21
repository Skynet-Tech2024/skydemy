from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    level = forms.ChoiceField(choices=UserProfile.LEVEL_CHOICES, required=True, label="Your Level")  # Now required
    whatsapp_number = forms.CharField(max_length=20, required=False, label="WhatsApp Number (optional)", help_text="For announcements and updates")
    avatar = forms.ImageField(required=False, label="Profile Picture", help_text="Upload a profile picture")
    captcha = CaptchaField(label="Enter the text shown below")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role', 'level', 'whatsapp_number', 'avatar', 'captcha']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create UserProfile with pending verification
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                level=self.cleaned_data['level'],  # Required, so always present
                whatsapp_number=self.cleaned_data.get('whatsapp_number', ''),  # Optional
                verification_status='pending',
                avatar=self.cleaned_data.get('avatar')
            )
        return user

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'level']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }