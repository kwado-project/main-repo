from django.contrib import admin

from .models import Examination, ExamSubject, StudentExam, Subject, Topic


class ExamSubjectInline(admin.TabularInline):
    model = ExamSubject
    extra = 1
    autocomplete_fields = ("subject",)


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "min_subjects", "max_subjects", "mock_duration_minutes", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "code", "full_name")
    prepopulated_fields = {"code": ("name",)}
    inlines = [ExamSubjectInline]


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "parent", "order", "weight", "is_active")
    list_filter = ("subject", "is_active")
    search_fields = ("name", "subject__name")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("subject", "parent")


@admin.register(StudentExam)
class StudentExamAdmin(admin.ModelAdmin):
    list_display = ("user", "examination", "exam_date", "daily_minutes", "onboarding_step", "is_archived")
    list_filter = ("examination", "onboarding_step", "is_archived")
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    filter_horizontal = ("subjects",)
