from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

# ===== STEP 1: Account Creation =====
class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label="I am a")
    phone_number = forms.CharField(max_length=20, required=False, label="Phone Number (optional, for recovery)")
    captcha = CaptchaField(label="Enter the text shown below")

    class Meta:
        model = User
        fields = ['username', 'phone_number', 'password', 'password_confirm', 'role']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and User.objects.filter(email=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


# ===== STEP 2: Profile Completion (optional) =====
class ProfileCompletionForm(forms.ModelForm):
    # Common fields for both roles
    avatar = forms.ImageField(required=False, label="Profile Photo")

    class Meta:
        model = UserProfile
        fields = ['role', 'level', 'whatsapp_number', 'avatar']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make level optional for teachers? Actually we can keep it required for now
        self.fields['level'].required = True
        self.fields['whatsapp_number'].required = False