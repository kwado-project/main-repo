from django.contrib import admin

from .models import ActivityPricing, CreditPackage, CreditTransaction, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "total_purchased", "total_earned", "total_spent")
    search_fields = ("user__email",)
    readonly_fields = ("balance", "total_purchased", "total_earned", "total_spent")


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "wallet", "kind", "amount", "balance_after", "description")
    list_filter = ("kind",)
    search_fields = ("wallet__user__email", "idempotency_key", "reference_id")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(CreditPackage)
admin.site.register(ActivityPricing)
