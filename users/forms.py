from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES)
    level = forms.ChoiceField(choices=UserProfile.LEVEL_CHOICES, required=True, label="Your Level")
    whatsapp_number = forms.CharField(max_length=20, required=False, label="WhatsApp Number (optional)", help_text="For announcements and updates")
    avatar = forms.ImageField(required=False, label="Profile Picture", help_text="Upload a profile picture")
    
    # ===== NEW: Identity Verification =====
    id_document = forms.FileField(
        required=False,
        label="Identity Document",
        help_text="Upload National ID, School ID, Driver's License, or International Passport"
    )
    id_document_type = forms.ChoiceField(
        choices=UserProfile.ID_DOCUMENT_TYPES,
        required=False,
        label="Document Type",
        help_text="Select the type of document you uploaded"
    )
    
    # ===== NEW: Location Verification =====
    utility_bill = forms.FileField(
        required=False,
        label="Utility Bill",
        help_text="Upload a utility bill (water, electricity, internet) with your name and address for location verification"
    )
    
    captcha = CaptchaField(label="Enter the text shown below")
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password1', 'password2', 
            'role', 'level', 'whatsapp_number', 'avatar',
            'id_document', 'id_document_type', 'utility_bill',
            'captcha'
        ]
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            # Create UserProfile with all fields
            profile = UserProfile.objects.create(
                user=user,
                role=self.cleaned_data['role'],
                level=self.cleaned_data['level'],
                whatsapp_number=self.cleaned_data.get('whatsapp_number', ''),
                verification_status='pending',
                avatar=self.cleaned_data.get('avatar'),
                # Identity fields
                id_document=self.cleaned_data.get('id_document'),
                id_document_type=self.cleaned_data.get('id_document_type'),
                # Location fields
                utility_bill=self.cleaned_data.get('utility_bill'),
                location_verified=False,  # Default until verified by admin
            )
        return user


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'level']
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }