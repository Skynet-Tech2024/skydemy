from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserProfile, Notification, Follow, Wishlist, ProgressHistory, WhatsAppAnnouncement, Message

# Unregister the default User admin (removes the "Users" link under Authentication and Authorization)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# Register UserProfile – fully editable (management allowed)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'verification_status', 'level', 'rating', 'total_lessons_completed', 'is_premium')
    list_filter = ('role', 'level', 'verification_status', 'is_premium', 'is_suspended')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('rating', 'total_lessons_completed')  # Keep these as read-only (auto-calculated)
    fields = ('user', 'role', 'level', 'verification_status', 'verification_notes', 
              'is_premium', 'subscription_expiry', 'is_suspended', 'avatar')
    list_display_links = ('user',)  # Click username to edit

    # Allow add, change, delete
    def has_add_permission(self, request):
        return True
    def has_change_permission(self, request, obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True

# Register other models (unchanged)
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title', 'message')

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'added_at')
    search_fields = ('user__username', 'lesson__title')

@admin.register(ProgressHistory)
class ProgressHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_lessons_completed', 'rating', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('user__username',)

@admin.register(WhatsAppAnnouncement)
class WhatsAppAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target', 'sent_by', 'sent_at', 'is_sent')
    list_filter = ('target', 'is_sent')
    search_fields = ('title', 'message')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'subject', 'content')