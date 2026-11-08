from django.contrib import admin

from .models import AuditLog, SystemSetting


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "target_type", "target_id", "ip_address")
    list_filter = ("action",)
    search_fields = ("target_id", "actor__email")
    readonly_fields = [f.name for f in AuditLog._meta.fields]


admin.site.register(SystemSetting)
