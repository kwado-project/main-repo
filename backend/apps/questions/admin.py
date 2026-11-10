from django.contrib import admin

from .models import AnswerKey, Passage, Question, QuestionOption


class OptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 0


class AnswerKeyInline(admin.StackedInline):
    """Read-only: answers are verified through the review workflow in the admin console."""

    model = AnswerKey
    can_delete = False
    readonly_fields = ("correct_option", "verified_by", "verified_at", "verification_source")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "subject", "topic", "difficulty", "status", "is_ai_generated", "created_at")
    list_filter = ("status", "subject", "difficulty", "is_ai_generated", "is_official_past_question")
    search_fields = ("text",)
    autocomplete_fields = ("subject", "topic")
    raw_id_fields = ("passage", "examination", "created_by")
    # Publishing must go through Import → Validate → Verify answer → Review → Publish.
    readonly_fields = ("status", "reviewed_by", "published_at")
    inlines = [OptionInline, AnswerKeyInline]


@admin.register(Passage)
class PassageAdmin(admin.ModelAdmin):
    search_fields = ("title", "body")
