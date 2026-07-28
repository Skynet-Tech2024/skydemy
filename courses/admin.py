from django.contrib import admin
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from .models import Subject, Course, Lesson, Progress, Exam, ExamResult, Certificate
from .forms import ExamCreationForm, CourseCreationForm, CertificateIssueForm
from users.utils import create_notification
from core.admin import admin_site
import os

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

    # ----- Override add_view to serve the custom course wizard -----
    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            form = CourseCreationForm(request.POST)
            if form.is_valid():
                course = form.save(commit=False)
                course.save()
                self.message_user(request, f"Course '{course.name}' created successfully!", messages.SUCCESS)
                return HttpResponseRedirect(reverse('admin:courses_course_changelist'))
            else:
                context = {
                    'title': 'Add Course',
                    'form': form,
                    'errors': form.errors,
                }
                return render(request, 'courses/create_course_wizard.html', context)

        form = CourseCreationForm()
        context = {
            'title': 'Create New Course',
            'form': form,
        }
        return render(request, 'courses/create_course_wizard.html', context)
    # ----- End override -----

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

    # REMOVED redirect so admin changelist shows all lessons
    # def changelist_view(self, request, extra_context=None):
    #     return redirect('lesson_list')


# ===== Progress Admin =====
class ProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'progress_percentage', 'completed', 'last_accessed')
    list_filter = ('completed',)


# ===== Exam Admin =====
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'exam_type', 'status', 'created_at')
    list_filter = ('status', 'exam_type', 'visibility')
    search_fields = ('title', 'exam_code')
    readonly_fields = ('exam_code', 'created_at', 'reviewed_at')
    autocomplete_fields = ('course', 'subject', 'reviewed_by', 'teacher')
    exclude = ('exam_document', 'marking_guide_document', 'manual_review_required')
    actions = ['upload_exam_documents']

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
            ),
            'classes': ('col2',),
        }),
    )

    # ----- CUSTOM ACTION: Upload exam documents -----
    def upload_exam_documents(self, request, queryset):
        if 'apply' in request.POST:
            file = request.FILES.get('exam_file')
            if not file:
                self.message_user(request, "No file selected.", messages.ERROR)
                return HttpResponseRedirect(request.get_full_path())

            allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                self.message_user(
                    request,
                    f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
                    messages.ERROR
                )
                return HttpResponseRedirect(request.get_full_path())

            for exam in queryset:
                exam.exam_document = file
                exam.save()

            self.message_user(
                request,
                f"File '{file.name}' uploaded successfully for {queryset.count()} exam(s).",
                messages.SUCCESS
            )
            return HttpResponseRedirect(request.get_full_path())

        context = {
            'title': 'Upload Exam Documents',
            'queryset': queryset,
            'action_checkbox_name': admin.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        }
        return render(request, 'admin/upload_exam_documents.html', context)

    upload_exam_documents.short_description = "Upload exam documents (PDF/DOC/DOCX/Excel)"
    # ----- End custom action -----

    # ----- Override add_view to serve the custom exam wizard -----
    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            form = ExamCreationForm(request.POST, request.FILES)
            if form.is_valid():
                exam = form.save(commit=False)
                exam.exam_code = f"EXAM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                exam.status = 'pending'
                exam.save()

                if form.cleaned_data.get('exam_paper'):
                    exam.exam_document = form.cleaned_data['exam_paper']
                if form.cleaned_data.get('marking_guide'):
                    exam.marking_guide_document = form.cleaned_data['marking_guide']
                exam.save()

                self.message_user(request, f"Exam '{exam.title}' created successfully!", messages.SUCCESS)
                return HttpResponseRedirect(reverse('admin:courses_exam_changelist'))
            else:
                context = {
                    'title': 'Add Exam',
                    'form': form,
                    'errors': form.errors,
                }
                return render(request, 'courses/create_exam_wizard.html', context)

        form = ExamCreationForm()
        context = {
            'title': 'Create New Exam',
            'form': form,
        }
        return render(request, 'courses/create_exam_wizard.html', context)
    # ----- End override -----

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

    # ----- Override add_view to serve the custom certificate wizard -----
    def add_view(self, request, form_url='', extra_context=None):
        if request.method == 'POST':
            form = CertificateIssueForm(request.POST)
            if form.is_valid():
                achievement_type = form.cleaned_data['achievement_type']
                user = form.cleaned_data['user']
                lesson = form.cleaned_data.get('lesson')
                exam = form.cleaned_data.get('exam')
                issue_date = form.cleaned_data['issue_date']
                certificate_number = form.cleaned_data.get('certificate_number')

                if achievement_type == 'lesson' and lesson:
                    certificate = Certificate.objects.create(
                        user=user,
                        lesson=lesson,
                        certificate_number=certificate_number,
                        issued_date=issue_date,
                    )
                    self.message_user(request, f"Certificate issued to {user.username} for lesson '{lesson.title}'.", messages.SUCCESS)
                    return HttpResponseRedirect(reverse('admin:courses_certificate_changelist'))

                elif achievement_type == 'exam' and exam:
                    if hasattr(Certificate, 'exam'):
                        certificate = Certificate.objects.create(
                            user=user,
                            exam=exam,
                            certificate_number=certificate_number,
                            issued_date=issue_date,
                        )
                        self.message_user(request, f"Certificate issued to {user.username} for exam '{exam.title}'.", messages.SUCCESS)
                    elif exam.lesson:
                        certificate = Certificate.objects.create(
                            user=user,
                            lesson=exam.lesson,
                            certificate_number=certificate_number,
                            issued_date=issue_date,
                        )
                        self.message_user(request, f"Certificate issued to {user.username} for exam '{exam.title}' (linked to lesson).", messages.SUCCESS)
                    else:
                        messages.error(request, "This exam has no associated lesson. Cannot issue certificate.")
                        context = {
                            'title': 'Issue Certificate',
                            'form': form,
                            'errors': form.errors,
                        }
                        return render(request, 'courses/issue_certificate_wizard.html', context)
                    return HttpResponseRedirect(reverse('admin:courses_certificate_changelist'))

                else:
                    messages.error(request, "Please select a valid achievement.")
                    context = {
                        'title': 'Issue Certificate',
                        'form': form,
                        'errors': form.errors,
                    }
                    return render(request, 'courses/issue_certificate_wizard.html', context)

                return HttpResponseRedirect(reverse('admin:courses_certificate_changelist'))
            else:
                context = {
                    'title': 'Issue Certificate',
                    'form': form,
                    'errors': form.errors,
                }
                return render(request, 'courses/issue_certificate_wizard.html', context)

        form = CertificateIssueForm()
        context = {
            'title': 'Issue New Certificate',
            'form': form,
        }
        return render(request, 'courses/issue_certificate_wizard.html', context)
    # ----- End override -----

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