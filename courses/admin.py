from django.contrib import admin
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from .models import Subject, Course, Lesson, Progress, Exam, ExamResult, Certificate
from users.utils import create_notification
from core.admin import admin_site

# ===== Subject Admin =====
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'level', 'status', 'proposed_by', 'created_at')
    list_filter = ('level', 'status')
    search_fields = ('name',)
    actions = ['approve_subjects', 'reject_subjects', 'delete_selected_subjects']

    def changelist_view(self, request, extra_context=None):
        return redirect('subject_list')

    def approve_subjects(self, request, queryset):
        count = queryset.update(status='approved')
        self.message_user(request, f"{count} subject(s) approved.", messages.SUCCESS)
    approve_subjects.short_description = "Approve selected subjects"

    def reject_subjects(self, request, queryset):
        count = queryset.update(status='rejected')
        self.message_user(request, f"{count} subject(s) rejected.", messages.SUCCESS)
    reject_subjects.short_description = "Reject selected subjects"

    def delete_selected_subjects(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} subject(s) deleted.", messages.SUCCESS)
    delete_selected_subjects.short_description = "Delete selected subjects"


# ===== Course Admin =====
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('code', 'name')
    readonly_fields = ('status',)

    def get_fields(self, request, obj=None):
        if obj:
            return ('name', 'code', 'description', 'status')
        else:
            return ('name', 'code', 'description')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.status = 'pending'
            create_notification(
                user=request.user,
                notification_type='system',
                title='📚 Course Submitted for Review',
                message=f'Your course "{obj.name}" has been submitted for review.',
                link='/dashboard/courses/'
            )
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(
            request,
            f'✅ Course "{obj.name}" has been submitted for review.',
            messages.SUCCESS
        )
        return redirect('course_list')

    def changelist_view(self, request, extra_context=None):
        return redirect('course_list')


# ===== Lesson Admin =====
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'status', 'teacher', 'created_at', 'views')
    list_filter = ('level', 'status', 'teacher')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'views')
    actions = ['approve_lessons', 'reject_lessons']

    def get_fields(self, request, obj=None):
        if obj:
            return ('title', 'level', 'description', 'subject', 'course',
                    'pdf_file', 'original_file', 'is_converted', 'converted_html',
                    'video_url', 'video_file', 'status', 'admin_notes')
        else:
            return ('title', 'level', 'description', 'subject', 'course',
                    'pdf_file', 'original_file', 'is_converted', 'converted_html',
                    'video_url', 'video_file')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subject":
            kwargs["queryset"] = Subject.objects.filter(status='approved')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.status = 'pending'
            obj.teacher = request.user
            create_notification(
                user=request.user,
                notification_type='system',
                title='📖 Lesson Submitted for Review',
                message=f'Your lesson "{obj.title}" has been submitted for review.',
                link='/dashboard/lessons/'
            )
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(
            request,
            f'✅ Lesson "{obj.title}" has been submitted for review.',
            messages.SUCCESS
        )
        return redirect('lesson_list')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def approve_lessons(self, request, queryset):
        updated = 0
        for lesson in queryset:
            lesson.status = 'approved'
            lesson.reviewed_by = request.user
            lesson.reviewed_at = datetime.now()
            lesson.save()
            updated += 1
            create_notification(
                user=lesson.teacher,
                notification_type='lesson_approved',
                title='✅ Lesson Approved!',
                message=f'Your lesson "{lesson.title}" has been approved and is now live on the platform.',
                link=f'/courses/lesson/{lesson.id}/'
            )
        self.message_user(request, f'{updated} lesson(s) approved.')
    approve_lessons.short_description = "Approve selected lessons"

    def reject_lessons(self, request, queryset):
        updated = 0
        for lesson in queryset:
            lesson.status = 'rejected'
            lesson.reviewed_by = request.user
            lesson.reviewed_at = datetime.now()
            lesson.save()
            updated += 1
            create_notification(
                user=lesson.teacher,
                notification_type='system',
                title='❌ Lesson Rejected',
                message=f'Your lesson "{lesson.title}" has been rejected. Please review and resubmit.'
            )
        self.message_user(request, f'{updated} lesson(s) rejected.')
    reject_lessons.short_description = "Reject selected lessons"

    def changelist_view(self, request, extra_context=None):
        return redirect('lesson_list')


# ===== Progress Admin =====
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'progress_percentage', 'completed', 'last_accessed')
    list_filter = ('completed',)


# ===== Exam Admin (without date restrictions, with autocomplete) =====
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam_type', 'status', 'created_at')
    list_filter = ('status', 'exam_type', 'visibility')
    search_fields = ('title', 'exam_code')
    readonly_fields = ('exam_code', 'created_at', 'reviewed_at')
    autocomplete_fields = ('course', 'subject', 'reviewed_by', 'teacher')

    fieldsets = (
        ('📘 Exam Information', {
            'fields': (
                ('title', 'exam_type'),
                ('course', 'subject'),
                ('academic_session', 'term'),
                ('level', 'language'),
                ('exam_code', 'duration_minutes'),
                ('total_marks', 'passing_score'),
                ('number_of_questions', 'instructions'),
            ),
            'classes': ('col2', 'wide'),
        }),
        ('🕒 Availability', {
            'fields': (
                ('time_limit_minutes', 'attempts_allowed'),
                ('question_order', 'answer_order'),
                ('show_result_immediately', 'show_correct_answers'),
                ('auto_submit', 'late_submission'),
            ),
            'classes': ('col2',),
        }),
        ('🔐 Access Control', {
            'fields': (
                ('visibility', 'require_password'),
                ('exam_password', 'require_safe_browser'),
                ('require_webcam', 'randomize_questions'),
            ),
            'classes': ('col2',),
        }),
        ('🎯 Grading', {
            'fields': (
                ('grading_method', 'negative_marking'),
                ('marks_per_question', 'auto_grade_objective'),
                ('manual_review_required',),
            ),
            'classes': ('col2',),
        }),
        ('📄 Exam Source', {
            'fields': (
                'exam_source',
                ('exam_document', 'marking_guide_document'),
            ),
            'classes': ('col2',),
        }),
        ('🛡️ Anti-cheating', {
            'fields': (
                ('shuffle_questions', 'shuffle_options'),
                ('fullscreen_mode', 'disable_copy_paste'),
                ('browser_lock', 'webcam_monitoring'),
                ('screen_recording', 'tab_switching_detection'),
                ('ip_restriction',),
            ),
            'classes': ('col2', 'collapse'),
        }),
        ('📢 Notifications', {
            'fields': (
                ('notify_immediately', 'notify_on_publish'),
                ('notify_before_deadline', 'notify_after_grading'),
            ),
            'classes': ('col2', 'collapse'),
        }),
        ('Approval Workflow', {
            'fields': ('status', 'admin_notes', 'reviewed_by', 'reviewed_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.status = 'pending'
            create_notification(
                user=request.user,
                notification_type='system',
                title='📝 Exam Submitted for Review',
                message=f'Your exam "{obj.title}" has been submitted for review.',
                link='/dashboard/exams/'
            )
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        self.message_user(
            request,
            f'✅ Exam "{obj.title}" has been submitted for review.',
            messages.SUCCESS
        )
        return redirect('exam_list')

    def changelist_view(self, request, extra_context=None):
        return redirect('exam_list')


# ===== ExamResult Admin =====
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'percentage', 'passed', 'date_taken')
    list_filter = ('passed',)

    def changelist_view(self, request, extra_context=None):
        return redirect('examresult_list')


# ===== Certificate Admin =====
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'certificate_number', 'issued_date')
    search_fields = ('certificate_number',)

    def changelist_view(self, request, extra_context=None):
        return redirect('certificate_list')


# ===== Register all models with the custom admin site =====
admin_site.register(Subject, SubjectAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Progress, ProgressAdmin)
admin_site.register(Exam, ExamAdmin)
admin_site.register(ExamResult, ExamResultAdmin)
admin_site.register(Certificate, CertificateAdmin)