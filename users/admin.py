from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'level', 'verification_status', 'is_premium', 'is_suspended')
    list_filter = ('role', 'level', 'verification_status', 'is_premium', 'is_suspended')
    search_fields = ('user__username', 'user__email', 'bio')
    readonly_fields = ('joined_date', 'updated_at', 'total_lessons_completed', 'rating')
    fieldsets = (
        ('User', {'fields': ('user', 'role')}),
        ('Profile Information', {'fields': ('bio', 'avatar', 'level', 'date_of_birth', 'address')}),
        ('Verification', {'fields': ('verification_status', 'verification_notes')}),
        ('Premium', {'fields': ('is_premium', 'subscription_expiry')}),
        ('Stats', {'fields': ('total_lessons_completed', 'rating', 'joined_date', 'updated_at')}),
        ('Suspension', {'fields': ('is_suspended',)}),
    )