from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.core.models import TimeStampedModel


class Referral(TimeStampedModel):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals_made")
    referred = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referred_by")
    code_used = models.CharField(max_length=12)

    class Meta:
        constraints = [models.CheckConstraint(condition=~Q(referrer=F("referred")), name="no_self_referral")]


class ReferralReward(TimeStampedModel):
    class Status(models.TextChoices):
        GRANTED = "granted"
        REVERSED = "reversed"

    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name="rewards")
    payment = models.OneToOneField("payments.Payment", on_delete=models.PROTECT, related_name="referral_reward")
    purchased_credits = models.PositiveIntegerField()
    reward_credits = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.GRANTED)
    transaction = models.ForeignKey("wallet.CreditTransaction", on_delete=models.PROTECT, related_name="+")
    reversal_transaction = models.ForeignKey(
        "wallet.CreditTransaction", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
