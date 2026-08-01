from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Level, Follow, SavedLesson, Message, Notification, ProgressHistory, WhatsAppAnnouncement, Activity


# ===== LEVEL ADMIN =====
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


# ===== USER PROFILE ADMIN =====
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'get_levels', 'role', 'verification_status', 'is_premium', 'is_suspended')
    list_filter = ('role', 'levels', 'verification_status', 'is_premium', 'is_suspended')
    search_fields = ('user__username', 'user__email', 'full_name', 'phone_number')
    readonly_fields = ('joined_date', 'updated_at', 'total_lessons_completed', 'rating')
    filter_horizontal = ('levels',)

    fieldsets = (
        ('User', {'fields': ('user', 'role')}),
        ('Profile Information', {'fields': ('full_name', 'bio', 'avatar', 'levels', 'phone_number')}),
        ('Verification', {'fields': ('verification_status', 'verification_notes')}),
        ('Premium', {'fields': ('is_premium', 'subscription_expiry')}),
        ('Stats', {'fields': ('total_lessons_completed', 'rating', 'joined_date', 'updated_at')}),
        ('Suspension', {'fields': ('is_suspended', 'is_deleted')}),
    )

    def get_levels(self, obj):
        return ", ".join([level.name for level in obj.levels.all()])
    get_levels.short_description = 'Level(s)'


# ===== REGISTER THE PROFILE (unregister if already registered) =====
try:
    admin.site.unregister(UserProfile)
except admin.sites.NotRegistered:
    pass
admin.site.register(UserProfile, UserProfileAdmin)


# ===== OPTIONAL: EXTEND USER ADMIN IF NEEDED =====
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')

try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, CustomUserAdmin)


# ===== OTHER MODELS =====
@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')


@admin.register(SavedLesson)
class SavedLessonAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'added_at')
    search_fields = ('user__username', 'lesson__title')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'subject', 'is_read', 'sent_at')
    search_fields = ('sender__username', 'receiver__username', 'subject')
    list_filter = ('is_read', 'sent_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    list_filter = ('notification_type', 'is_read', 'created_at')


@admin.register(ProgressHistory)
class ProgressHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_lessons_completed', 'rating', 'recorded_at')
    search_fields = ('user__username',)
    list_filter = ('recorded_at',)


@admin.register(WhatsAppAnnouncement)
class WhatsAppAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_audience', 'status', 'sent_at', 'created_by')
    search_fields = ('title', 'content')
    list_filter = ('target_audience', 'status', 'sent_at', 'created_at')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'description', 'created_at')
    search_fields = ('action', 'description', 'user__username')
    list_filter = ('action', 'created_at')


# ===== FALLBACK: ensure Level is registered (if decorator didn't work) =====
try:
    admin.site.register(Level)
except admin.sites.AlreadyRegistered:
    pass