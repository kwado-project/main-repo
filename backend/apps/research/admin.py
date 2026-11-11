from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import (CopyrightPermission, ExaminationYear, ExtractionJob, PastQuestion, ResearchTarget, Source,
                     SourceDocument, VerificationRecord)


class PermissionInline(admin.TabularInline):
    model = CopyrightPermission
    extra = 0
    readonly_fields = ("status", "basis", "scope", "evidence", "recorded_by", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False  # recorded through the admin console so the evidence rules apply


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("domain", "permission_status", "is_seed", "is_active", "discovered_via", "crawl_delay_seconds", "terms_checked_at")
    list_filter = ("permission_status", "is_seed", "is_active", "discovered_via")
    search_fields = ("domain", "name")
    readonly_fields = ("permission_status", "robots_txt", "robots_checked_at", "terms_flags", "terms_checked_at")
    inlines = [PermissionInline]


@admin.register(SourceDocument)
class SourceDocumentAdmin(ReadOnlyAdmin):
    list_display = ("url", "status", "kind", "subject", "year", "examination_guess", "classification_confidence")
    list_filter = ("status", "kind", "year")
    search_fields = ("url", "title")


@admin.register(PastQuestion)
class PastQuestionAdmin(ReadOnlyAdmin):
    list_display = ("id", "subject", "year", "question_number", "verification_status", "rights_status", "extraction_method", "extraction_confidence")
    list_filter = ("verification_status", "rights_status", "subject", "year", "extraction_method")
    search_fields = ("text",)


@admin.register(ResearchTarget)
class ResearchTargetAdmin(ReadOnlyAdmin):
    list_display = ("exam_year", "subject", "status", "documents_found", "questions_extracted", "questions_verified", "search_attempts")
    list_filter = ("status", "subject")


@admin.register(ExtractionJob)
class ExtractionJobAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "kind", "status", "attempts", "idempotency_key")
    list_filter = ("kind", "status")
    search_fields = ("idempotency_key", "error")


@admin.register(VerificationRecord)
class VerificationRecordAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "question", "check_name", "result", "actor", "user")
    list_filter = ("check_name", "result", "actor")


admin.site.register(ExaminationYear)
