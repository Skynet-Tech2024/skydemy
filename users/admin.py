from .models import UserProfile, WhatsAppAnnouncement
from django.contrib import admin
from django.utils.html import format_html
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('avatar_preview', 'user', 'status_light', 'role', 'level', 'rating_stars', 'total_lessons_completed', 'is_premium')
    list_filter = ('role', 'level', 'verification_status', 'is_suspended', 'is_premium')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('verification_status', 'last_active', 'rating')
    actions = ['approve_users', 'reject_users', 'suspend_users', 'unsuspend_users', 'update_ratings']
    
    def avatar_preview(self, obj):
        if obj.avatar and hasattr(obj.avatar, 'url') and obj.avatar.url != '/media/avatars/default.png':
            return format_html('<img src="{}" style="width:40px; height:40px; border-radius:50%; object-fit:cover;" />', obj.avatar.url)
        return '👤'  # Simple emoji fallback without format_html
    avatar_preview.short_description = "Avatar"
    
    def status_light(self, obj):
        status = obj.get_status()
        colors = {
            'Active': '#28a745',
            'Pending': '#ffc107',
            'Suspended': '#dc3545',
            'Rejected': '#6c757d',
            'Inactive': '#17a2b8',
        }
        color = colors.get(status, '#6c757d')
        return format_html(
            '<span style="display:inline-block; width:12px; height:12px; border-radius:50%; background-color:{}; margin-right:8px;"></span><span>{}</span>',
            color, status
        )
    status_light.short_description = "Status"
    
    def rating_stars(self, obj):
        try:
            if float(obj.rating) == 0:
                return "⭐ 0.00 (0%)"
            percentage = (float(obj.rating) / 5) * 100
            full_stars = int(obj.rating)
            half_star = 1 if obj.rating - full_stars >= 0.5 else 0
            stars = '★' * full_stars + ('½' if half_star else '')
            empty_stars = '☆' * (5 - full_stars - half_star)
            return f"{stars}{empty_stars} {obj.rating:.2f} ({percentage:.0f}%)"
        except:
            return f"⭐ {obj.rating:.2f}"
    rating_stars.short_description = "Rating"
    rating_stars.admin_order_field = 'rating'
    
    def update_ratings(self, request, queryset):
        updated = 0
        for profile in queryset:
            profile.update_rating()
            updated += 1
        self.message_user(request, f'{updated} user(s) ratings updated.')
    update_ratings.short_description = "Update ratings for selected users"
    
    def approve_users(self, request, queryset):
        updated = queryset.update(verification_status='verified')
        self.message_user(request, f'{updated} user(s) approved.')
    approve_users.short_description = "Approve selected users"
    
    def reject_users(self, request, queryset):
        updated = queryset.update(verification_status='rejected')
        self.message_user(request, f'{updated} user(s) rejected.')
    reject_users.short_description = "Reject selected users"
    
    def suspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=True)
        self.message_user(request, f'{updated} user(s) suspended.')
    suspend_users.short_description = "Suspend selected users"
    
    def unsuspend_users(self, request, queryset):
        updated = queryset.update(is_suspended=False)
        self.message_user(request, f'{updated} user(s) unsuspended.')
    unsuspend_users.short_description = "Unsuspend selected users"
@admin.register(WhatsAppAnnouncement)
class WhatsAppAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target', 'sent_by', 'sent_at', 'is_sent', 'recipient_count_display')
    list_filter = ('target', 'is_sent', 'sent_at')
    search_fields = ('title', 'message')
    readonly_fields = ('sent_at', 'sent_by', 'is_sent')
    actions = ['send_announcement']
    
    def recipient_count_display(self, obj):
        return obj.get_recipients().count()
    recipient_count_display.short_description = "Recipients"
    
    def send_announcement(self, request, queryset):
        from django.contrib import messages
        from django.utils import timezone
        
        sent_count = 0
        for announcement in queryset:
            if not announcement.is_sent:
                recipients = announcement.get_recipients()
                sent_count += recipients.count()
                announcement.is_sent = True
                announcement.sent_by = request.user
                announcement.save()
                messages.info(request, f'WhatsApp announcement "{announcement.title}" prepared for {sent_count} recipients.')
        
        if sent_count > 0:
            messages.success(request, f'Announcement sent to {sent_count} users via WhatsApp!')
        else:
            messages.warning(request, 'No new announcements were sent.')
    send_announcement.short_description = "Send WhatsApp Announcement"
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # New object
            obj.sent_by = request.user
        super().save_model(request, obj, form, change)
    
    fieldsets = (
        (None, {
            'fields': ('title', 'message', 'target')
        }),
        ('Status', {
            'fields': ('sent_by', 'sent_at', 'is_sent'),
            'classes': ('collapse',)
        }),
    )