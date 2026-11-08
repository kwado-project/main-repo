from django.conf import settings
from django.core.cache import cache
from django.db import models

from apps.core.models import TimeStampedModel


class AIConfig(TimeStampedModel):
    """Admin-editable per-purpose model routing and limits."""

    purpose = models.SlugField(max_length=40, unique=True)
    model = models.CharField(max_length=60, blank=True)
    effort = models.CharField(
        max_length=8, blank=True, choices=[(x, x) for x in ("low", "medium", "high", "xhigh", "max")]
    )
    max_tokens = models.PositiveIntegerField(null=True, blank=True)
    is_enabled = models.BooleanField(default=True)
    daily_user_limit = models.PositiveIntegerField(default=200)

    CACHE_KEY = "aiconfig:{}"

    @classmethod
    def get_cached(cls, purpose):
        key = cls.CACHE_KEY.format(purpose)
        data = cache.get(key)
        if data is None:
            row = cls.objects.filter(purpose=purpose).values("model", "effort", "max_tokens", "is_enabled",
                                                              "daily_user_limit").first()
            data = row or {}
            cache.set(key, data, 300)
        return data

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(self.CACHE_KEY.format(self.purpose))


class AIConversation(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_conversations")
    student_exam = models.ForeignKey("examinations.StudentExam", null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL)
    topic = models.ForeignKey("examinations.Topic", null=True, blank=True, on_delete=models.SET_NULL)
    question = models.ForeignKey("questions.Question", null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=160, default="New conversation")
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "-updated_at"])]


class AIMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    class Status(models.TextChoices):
        COMPLETE = "complete"
        FAILED = "failed"

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.COMPLETE)
    credits_charged = models.PositiveSmallIntegerField(default=0)
    model = models.CharField(max_length=60, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    is_mock = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class AIUsage(models.Model):
    """Per-call usage record for cost monitoring."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+")
    purpose = models.CharField(max_length=40, db_index=True)
    model = models.CharField(max_length=60)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_read_tokens = models.PositiveIntegerField(default=0)
    succeeded = models.BooleanField(default=True)
    error = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
