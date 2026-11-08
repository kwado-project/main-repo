from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        SUCCESS = "success"
        FAILED = "failed"
        ABANDONED = "abandoned"
        REFUNDED = "refunded"

    class Provider(models.TextChoices):
        PAYSTACK = "paystack"
        DEV_SANDBOX = "dev_sandbox"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    package = models.ForeignKey("wallet.CreditPackage", on_delete=models.PROTECT)
    reference = models.CharField(max_length=64, unique=True)
    provider = models.CharField(max_length=20, choices=Provider.choices, default=Provider.PAYSTACK)
    amount_kobo = models.PositiveBigIntegerField()
    credits = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)
    authorization_url = models.URLField(max_length=500, blank=True)
    gateway_response = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=30, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    credit_transaction = models.OneToOneField(
        "wallet.CreditTransaction", null=True, blank=True, on_delete=models.PROTECT, related_name="payment"
    )
    raw_verification = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]


class WebhookEvent(TimeStampedModel):
    """Every received webhook, for idempotency and audit."""

    provider = models.CharField(max_length=20)
    event = models.CharField(max_length=60)
    event_id = models.CharField(max_length=120, unique=True)
    payload = models.JSONField()
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
