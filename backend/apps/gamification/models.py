from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class XPTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_transactions")
    amount = models.IntegerField()
    reason = models.CharField(max_length=120)
    source_type = models.CharField(max_length=40, blank=True)
    source_id = models.CharField(max_length=60, blank=True)
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL)
    idempotency_key = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]


class Streak(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="streak")
    current = models.PositiveIntegerField(default=0)
    longest = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)
    freezes_available = models.PositiveSmallIntegerField(default=1)


class ActivityDay(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_days")
    date = models.DateField()
    xp = models.PositiveIntegerField(default=0)
    questions_answered = models.PositiveIntegerField(default=0)
    minutes = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "date")]
        indexes = [models.Index(fields=["date", "-xp"])]


class Badge(TimeStampedModel):
    class Tier(models.TextChoices):
        BRONZE = "bronze"
        SILVER = "silver"
        GOLD = "gold"
        EMERALD = "emerald"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=40, default="award")
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.BRONZE)
    criteria = models.JSONField(default=dict, help_text='e.g. {"type": "streak", "value": 7}')
    xp_reward = models.PositiveSmallIntegerField(default=50)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class StudentBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    class Meta:
        unique_together = [("user", "badge")]


class Mission(TimeStampedModel):
    class Period(models.TextChoices):
        DAILY = "daily"
        WEEKLY = "weekly"

    class Metric(models.TextChoices):
        QUESTIONS_ANSWERED = "questions_answered"
        CORRECT_ANSWERS = "correct_answers"
        LESSONS_COMPLETED = "lessons_completed"
        QUIZZES_COMPLETED = "quizzes_completed"
        TUTOR_QUESTIONS = "tutor_questions"
        WEAK_TOPIC_PRACTICE = "weak_topic_practice"
        XP_EARNED = "xp_earned"

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=120)
    period = models.CharField(max_length=8, choices=Period.choices)
    metric = models.CharField(max_length=24, choices=Metric.choices)
    target = models.PositiveIntegerField()
    xp_reward = models.PositiveSmallIntegerField(default=20)
    icon = models.CharField(max_length=40, default="target")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class StudentMission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="missions")
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    period_start = models.DateField()
    progress = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "mission", "period_start")]
