from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import Badge, Mission, Streak, XPTransaction


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tier", "xp_reward", "order")


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ("title", "period", "metric", "target", "xp_reward", "is_active")
    list_editable = ("is_active",)


@admin.register(Streak)
class StreakAdmin(ReadOnlyAdmin):
    list_display = ("user", "current", "longest", "last_active_date", "freezes_available")
    search_fields = ("user__email",)


@admin.register(XPTransaction)
class XPTransactionAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "user", "amount", "reason")
    search_fields = ("user__email", "reason")
