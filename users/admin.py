from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile, Follow, Wishlist, Message, Notification,
    ProgressHistory, WhatsAppAnnouncement
)

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'level', 'verification_status', 'is_premium', 'is_suspended')
    list_filter = ('role', 'level', 'verification_status', 'is_premium', 'is_suspended')
    search_fields = ('user__username', 'user__email', 'bio')
    readonly_fields = ('joined_date', 'updated_at', 'total_lessons_completed', 'rating')
    fieldsets = (
        ('User', {
            'fields': ('user', 'role')
        }),
        ('Profile Information', {
            'fields': ('bio', 'avatar', 'level', 'date_of_birth', 'address')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verification_notes')
        }),
        ('Premium', {
            'fields': ('is_premium', 'subscription_expiry')
        }),
        ('Stats', {
            'fields': ('total_lessons_completed', 'rating', 'joined_date', 'updated_at')
        }),
        ('Suspension', {
            'fields': ('is_suspended',)
        }),
    )

class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    list_filter = ('created_at',)

class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'added_at')
    list_filter = ('added_at',)

class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'subject', 'is_read', 'sent_at')
    list_filter = ('is_read', 'sent_at')
    search_fields = ('sender__username', 'receiver__username', 'subject', 'content')

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')

class ProgressHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_lessons_completed', 'rating', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('user__username',)

class WhatsAppAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_audience', 'status', 'created_by', 'created_at')
    list_filter = ('target_audience', 'status', 'created_at')
    search_fields = ('title', 'content', 'created_by__username')

# Register models
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(ProgressHistory, ProgressHistoryAdmin)
admin.site.register(WhatsAppAnnouncement, WhatsAppAnnouncementAdmin)