from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=150, label="Username")
    phone_number = forms.CharField(max_length=20, required=False, label="Phone Number (optional, for recovery)")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label="I am a")
    captcha = CaptchaField(label="Enter the text shown below")

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data