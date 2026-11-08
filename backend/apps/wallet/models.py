from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class Wallet(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.IntegerField(default=0)
    total_purchased = models.PositiveIntegerField(default=0)
    total_earned = models.PositiveIntegerField(default=0)
    total_spent = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(balance__gte=0), name="wallet_balance_non_negative")]

    def __str__(self):
        return f"{self.user} · {self.balance} credits"


class CreditTransaction(models.Model):
    """Append-only ledger. Never updated or deleted after creation."""

    class Kind(models.TextChoices):
        PURCHASE = "purchase", "Credit purchase"
        SIGNUP_BONUS = "signup_bonus", "Welcome bonus"
        REFERRAL_REWARD = "referral_reward", "Referral reward"
        SPEND = "spend", "Activity"
        REFUND = "refund", "Refund"
        REVERSAL = "reversal", "Reversal"
        ADJUSTMENT = "adjustment", "Admin adjustment"

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    amount = models.IntegerField(help_text="Signed: positive = credit, negative = debit")
    balance_after = models.IntegerField()
    idempotency_key = models.CharField(max_length=120, unique=True)
    activity_key = models.CharField(max_length=40, blank=True)
    description = models.CharField(max_length=255)
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.CharField(max_length=80, blank=True)
    related = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]


class CreditPackage(TimeStampedModel):
    name = models.CharField(max_length=40)
    slug = models.SlugField(unique=True)
    credits = models.PositiveIntegerField()
    price_kobo = models.PositiveBigIntegerField(help_text="Price in kobo (₦1 = 100 kobo)")
    bonus_label = models.CharField(max_length=60, blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "credits"]

    def __str__(self):
        return f"{self.name} ({self.credits} credits)"

    @property
    def price_naira(self):
        return self.price_kobo // 100


class ActivityPricing(TimeStampedModel):
    key = models.SlugField(max_length=40, unique=True)
    label = models.CharField(max_length=80)
    credits = models.PositiveSmallIntegerField()
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["credits", "label"]

    def __str__(self):
        return f"{self.label}: {self.credits}"
