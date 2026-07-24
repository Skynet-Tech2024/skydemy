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
        # Redirect to custom Subjects dashboard page
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
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

    def changelist_view(self, request, extra_context=None):
        # Redirect to custom Course dashboard page
        return redirect('course_list')


# ===== Lesson Admin =====
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'status', 'teacher', 'created_at', 'views')
    list_filter = ('level', 'status', 'teacher')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'views')
    actions = ['approve_lessons', 'reject_lessons']

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
        if request.method == 'POST' and request.POST.get('action') in ['delete_selected', 'approve_lessons', 'reject_lessons']:
            action = request.POST.get('action')
            if not request.POST.get('confirm'):
                selected_pks = request.POST.getlist('_selected_action')
                if not selected_pks:
                    messages.warning(request, "No items selected.")
                    return HttpResponseRedirect(request.get_full_path())
                action_display = {
                    'delete_selected': 'Delete',
                    'approve_lessons': 'Approve',
                    'reject_lessons': 'Reject'
                }.get(action, action)
                context = {
                    'selected_pks': selected_pks,
                    'selected_count': len(selected_pks),
                    'action': action,
                    'action_display': action_display,
                    'is_popup': request.GET.get('_popup', False),
                    'to_field': request.GET.get('to_field', None),
                }
                return render(request, 'admin/courses/lesson/action_confirmation.html', context)
            else:
                selected_pks = request.POST.getlist('_selected_action')
                if not selected_pks:
                    messages.warning(request, "No items selected.")
                    return HttpResponseRedirect(request.get_full_path())
                queryset = Lesson.objects.filter(pk__in=selected_pks)
                if action == 'delete_selected':
                    count = queryset.count()
                    queryset.delete()
                    messages.success(request, f"Successfully deleted {count} lesson(s).")
                elif action == 'approve_lessons':
                    self.approve_lessons(request, queryset)
                elif action == 'reject_lessons':
                    self.reject_lessons(request, queryset)
                return HttpResponseRedirect(reverse('admin:courses_lesson_changelist'))
        return super().changelist_view(request, extra_context)


# ===== Progress Admin =====
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'progress_percentage', 'completed', 'last_accessed')
    list_filter = ('completed',)


# ===== Exam Admin =====
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'status', 'passing_score', 'created_at')
    list_filter = ('status', 'lesson__level')
    search_fields = ('title', 'lesson__title')
    actions = ['approve_exams', 'reject_exams']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def approve_exams(self, request, queryset):
        updated = 0
        for exam in queryset:
            exam.status = 'approved'
            exam.reviewed_by = request.user
            exam.reviewed_at = datetime.now()
            exam.save()
            updated += 1
            create_notification(
                user=exam.lesson.teacher,
                notification_type='system',
                title='📝 Exam Approved!',
                message=f'Your exam "{exam.title}" for lesson "{exam.lesson.title}" has been approved.',
                link=f'/courses/lesson/{exam.lesson.id}/'
            )
        self.message_user(request, f'{updated} exam(s) approved.')
    approve_exams.short_description = "Approve selected exams"

    def reject_exams(self, request, queryset):
        updated = 0
        for exam in queryset:
            exam.status = 'rejected'
            exam.reviewed_by = request.user
            exam.reviewed_at = datetime.now()
            exam.save()
            updated += 1
            create_notification(
                user=exam.lesson.teacher,
                notification_type='system',
                title='❌ Exam Rejected',
                message=f'Your exam "{exam.title}" for lesson "{exam.lesson.title}" has been rejected.'
            )
        self.message_user(request, f'{updated} exam(s) rejected.')
    reject_exams.short_description = "Reject selected exams"

    def changelist_view(self, request, extra_context=None):
        # Redirect to custom Exam dashboard page
        return redirect('exam_list')


# ===== ExamResult Admin =====
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'percentage', 'passed', 'date_taken')
    list_filter = ('passed',)


# ===== Certificate Admin =====
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'certificate_number', 'issued_date')
    search_fields = ('certificate_number',)

    def changelist_view(self, request, extra_context=None):
        # Redirect to custom Certificate dashboard page
        return redirect('certificate_list')


# ===== Register all models with the custom admin site =====
admin_site.register(Subject, SubjectAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Progress, ProgressAdmin)
admin_site.register(Exam, ExamAdmin)
admin_site.register(ExamResult, ExamResultAdmin)
admin_site.register(Certificate, CertificateAdmin)