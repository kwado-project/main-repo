from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import StudyMaterial


@admin.register(StudyMaterial)
class StudyMaterialAdmin(ReadOnlyAdmin):
    """Metadata only — student documents and analyses stay private."""

    list_display = ("title", "owner", "visibility", "status", "content_type", "size_bytes", "created_at")
    list_filter = ("status", "visibility")
    fields = ("title", "owner", "visibility", "status", "content_type", "size_bytes", "created_at")
