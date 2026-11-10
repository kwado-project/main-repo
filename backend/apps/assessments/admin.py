from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import QuizAttempt, TopicMastery


@admin.register(QuizAttempt)
class QuizAttemptAdmin(ReadOnlyAdmin):
    list_display = ("id", "user", "kind", "mode", "status", "subject", "score_percent", "credits_charged", "created_at")
    list_filter = ("kind", "mode", "status")
    search_fields = ("user__email",)


@admin.register(TopicMastery)
class TopicMasteryAdmin(ReadOnlyAdmin):
    list_display = ("user", "topic", "mastery", "attempts", "correct", "last_practised_at")
    search_fields = ("user__email", "topic__name")
