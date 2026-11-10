from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "kind", "title", "read_at")
    list_filter = ("kind",)
    search_fields = ("user__email", "title")
    raw_id_fields = ("user",)
