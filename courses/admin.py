from django.contrib import admin
from datetime import datetime
from .models import Subject, Course, Lesson, Progress, Exam, ExamResult, Certificate
from users.utils import create_notification
from core.admin import admin_site

# ===== Subject Admin =====
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'level')
    list_filter = ('level',)

# ===== Course Admin =====
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

# ===== Lesson Admin =====
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'status', 'teacher', 'created_at', 'views')
    list_filter = ('level', 'status', 'teacher')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'views')
    actions = ['approve_lessons', 'reject_lessons']
    
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

# ===== ExamResult Admin =====
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam', 'percentage', 'passed', 'date_taken')
    list_filter = ('passed',)

# ===== Certificate Admin =====
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'certificate_number', 'issued_date')
    search_fields = ('certificate_number',)

# ===== Register all models with the custom admin site =====
admin_site.register(Subject, SubjectAdmin)
admin_site.register(Course, CourseAdmin)
admin_site.register(Lesson, LessonAdmin)
admin_site.register(Progress, ProgressAdmin)
admin_site.register(Exam, ExamAdmin)
admin_site.register(ExamResult, ExamResultAdmin)
admin_site.register(Certificate, CertificateAdmin)