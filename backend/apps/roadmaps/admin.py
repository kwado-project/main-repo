from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import Roadmap


@admin.register(Roadmap)
class RoadmapAdmin(ReadOnlyAdmin):
    list_display = ("id", "student_exam", "version", "is_current", "start_date", "end_date", "created_at")
    list_filter = ("is_current",)
    search_fields = ("student_exam__user__email",)
