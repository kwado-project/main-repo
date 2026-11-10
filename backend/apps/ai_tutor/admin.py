from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import AIConfig, AIConversation, AIUsage


@admin.register(AIConfig)
class AIConfigAdmin(admin.ModelAdmin):
    list_display = ("purpose", "model", "effort", "max_tokens", "daily_user_limit", "is_enabled")


@admin.register(AIConversation)
class AIConversationAdmin(ReadOnlyAdmin):
    """Metadata only — message contents are private to the student."""

    list_display = ("id", "user", "title", "subject", "created_at", "updated_at")
    fields = ("user", "subject", "topic", "created_at")
    search_fields = ("user__email",)


@admin.register(AIUsage)
class AIUsageAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "user", "purpose", "model", "input_tokens", "output_tokens", "succeeded", "error")
    list_filter = ("purpose", "succeeded")
