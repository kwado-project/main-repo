from django.contrib import admin

from apps.core.admin_utils import ReadOnlyAdmin

from .models import Referral, ReferralReward


@admin.register(Referral)
class ReferralAdmin(ReadOnlyAdmin):
    list_display = ("referrer", "referred", "code_used", "created_at")
    search_fields = ("referrer__email", "referred__email", "code_used")


@admin.register(ReferralReward)
class ReferralRewardAdmin(ReadOnlyAdmin):
    list_display = ("referral", "payment", "purchased_credits", "reward_credits", "status", "created_at")
    list_filter = ("status",)
