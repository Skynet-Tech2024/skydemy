from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.urls import path
from .models import UserProfile, Notification, Follow, Wishlist, ProgressHistory, WhatsAppAnnouncement, Message

# Import the custom admin site from core.admin
from core.admin import admin_site

# ===== UserProfile Admin =====
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user_full_info', 'role_badge', 'verification_badge', 'level_display', 'rating_display', 'premium_badge')
    list_filter = ('role', 'level', 'verification_status', 'is_premium', 'is_suspended')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('rating', 'total_lessons_completed')
    fields = ('user', 'role', 'level', 'verification_status', 'verification_notes', 
              'is_premium', 'subscription_expiry', 'is_suspended', 'avatar')
    list_display_links = None
    actions = ['verify_selected', 'suspend_selected', 'activate_selected']

    def has_add_permission(self, request):
        return True
    def has_change_permission(self, request, obj=None):
        return True
    def has_delete_permission(self, request, obj=None):
        return True

    # ===== CUSTOM DISPLAY METHODS =====
    def user_full_info(self, obj):
        full_name = obj.user.get_full_name().strip()
        display_name = full_name if full_name else obj.user.username
        email = obj.user.email or 'No email'
        return format_html(
            '<div><strong style="font-size:15px;">👤 {}</strong><br>'
            '<span style="font-size:12px;color:#6c757d;">📧 {}</span><br>'
            '<span style="font-size:11px;color:#6c757d;">Joined: {}</span></div>',
            display_name,
            email,
            obj.user.date_joined.strftime('%d %b %Y')
        )
    user_full_info.short_description = 'User'

    def role_badge(self, obj):
        colors = {
            'teacher': '#0B8A4A',
            'learner': '#2563EB',
            'admin': '#D4AF37'
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background:{};color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            color,
            obj.get_role_display()
        )
    role_badge.short_description = 'Role'

    def verification_badge(self, obj):
        if obj.verification_status == 'verified':
            return format_html('<span style="background:#0B8A4A;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">🟢 Verified</span>')
        elif obj.verification_status == 'pending':
            return format_html('<span style="background:#D4AF37;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">🟡 Pending Review</span>')
        elif obj.verification_status == 'rejected':
            return format_html('<span style="background:#dc3545;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">🔴 Rejected</span>')
        return format_html('<span style="background:#6c757d;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">Unknown</span>')
    verification_badge.short_description = 'Status'

    def level_display(self, obj):
        levels = {
            'primary': '🏫 Primary School',
            'secondary': '🏛️ Secondary School',
            'university': '🎓 University'
        }
        return levels.get(obj.level, '—')
    level_display.short_description = 'Level'

    def rating_display(self, obj):
        rating = float(obj.rating)
        full_stars = int(rating)
        empty_stars = 5 - full_stars
        return format_html(
            '<span style="color:#D4AF37;font-size:14px;">{}{} {:.1f}</span>',
            '★' * full_stars,
            '☆' * empty_stars,
            rating
        )
    rating_display.short_description = 'Rating'

    def premium_badge(self, obj):
        if obj.is_premium:
            return format_html('<span style="background:#D4AF37;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;">⭐ Premium</span>')
        return format_html('<span style="background:#e9ecef;color:#6c757d;padding:4px 12px;border-radius:20px;font-size:12px;">Free</span>')
    premium_badge.short_description = 'Premium'

    # ===== CUSTOM BULK ACTIONS =====
    def verify_selected(self, request, queryset):
        count = queryset.update(verification_status='verified')
        self.message_user(request, f'✅ {count} user(s) verified successfully.')
    verify_selected.short_description = '✅ Verify selected users'

    def suspend_selected(self, request, queryset):
        count = queryset.update(is_suspended=True)
        self.message_user(request, f'🚫 {count} user(s) suspended.')
    suspend_selected.short_description = '🚫 Suspend selected users'

    def activate_selected(self, request, queryset):
        count = queryset.update(is_suspended=False)
        self.message_user(request, f'✅ {count} user(s) activated.')
    activate_selected.short_description = '✅ Activate selected users'

    # ===== CUSTOM SINGLE-ACTION VIEWS (GET) =====
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('verify/<int:profile_id>/', self.admin_site.admin_view(self.verify_view), name='verify_user'),
            path('delete/<int:profile_id>/', self.admin_site.admin_view(self.delete_view), name='delete_user'),
            path('premium/<int:profile_id>/', self.admin_site.admin_view(self.premium_view), name='make_premium'),
        ]
        return custom_urls + urls

    def verify_view(self, request, profile_id):
        profile = get_object_or_404(UserProfile, id=profile_id)
        if request.method == 'GET':
            if request.GET.get('confirm', 'no') == 'yes':
                profile.verification_status = 'verified'
                profile.save()
                self.message_user(request, f'✅ User "{profile.user.get_full_name() or profile.user.username}" verified successfully.')
                return redirect(request.META.get('HTTP_REFERER', '/admin/users/userprofile/'))
            else:
                return self.admin_site.admin_view(
                    lambda r: render(
                        r,
                        'admin/users/userprofile/confirm_verify.html',
                        {'profile': profile, 'action': 'Verify'}
                    )
                )(request)
        return redirect('/admin/users/userprofile/')

    def delete_view(self, request, profile_id):
        profile = get_object_or_404(UserProfile, id=profile_id)
        if request.method == 'GET':
            if request.GET.get('confirm', 'no') == 'yes':
                user = profile.user
                profile.delete()
                user.delete()
                self.message_user(request, f'🗑️ User "{user.get_full_name() or user.username}" deleted successfully.')
                return redirect(request.META.get('HTTP_REFERER', '/admin/users/userprofile/'))
            else:
                return self.admin_site.admin_view(
                    lambda r: render(
                        r,
                        'admin/users/userprofile/confirm_delete.html',
                        {'profile': profile, 'action': 'Delete'}
                    )
                )(request)
        return redirect('/admin/users/userprofile/')

    def premium_view(self, request, profile_id):
        profile = get_object_or_404(UserProfile, id=profile_id)
        if request.method == 'GET':
            if request.GET.get('confirm', 'no') == 'yes':
                profile.is_premium = not profile.is_premium
                profile.save()
                status = "⭐ Premium" if profile.is_premium else "Free"
                self.message_user(request, f'User "{profile.user.get_full_name() or profile.user.username}" is now {status}.')
                return redirect(request.META.get('HTTP_REFERER', '/admin/users/userprofile/'))
            else:
                return redirect(request.META.get('HTTP_REFERER', '/admin/users/userprofile/'))
        return redirect('/admin/users/userprofile/')

    change_list_template = 'admin/users/userprofile/change_list.html'

# ===== Other Admin Classes =====
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title', 'message')

class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')

class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'added_at')
    search_fields = ('user__username', 'lesson__title')

class ProgressHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_lessons_completed', 'rating', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('user__username',)

class WhatsAppAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'target', 'sent_by', 'sent_at', 'is_sent')
    list_filter = ('target', 'is_sent')
    search_fields = ('title', 'message')

class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('sender__username', 'receiver__username', 'subject', 'content')

# ===== Register all models with the custom admin site =====
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(Notification, NotificationAdmin)
admin_site.register(Follow, FollowAdmin)
admin_site.register(Wishlist, WishlistAdmin)
admin_site.register(ProgressHistory, ProgressHistoryAdmin)
admin_site.register(WhatsAppAnnouncement, WhatsAppAnnouncementAdmin)
admin_site.register(Message, MessageAdmin)