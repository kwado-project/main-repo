from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import Payment, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    """Read-only: verify or refund from the admin console so the wallet ledger stays consistent."""

    list_display = ("reference", "user", "package", "amount_kobo", "credits", "status", "provider", "created_at")
    list_filter = ("status", "provider")
    search_fields = ("reference", "user__email")


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "provider", "event", "event_id", "processed_at", "error")
    list_filter = ("provider", "event")
    search_fields = ("event_id",)
