from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class QuizAttempt(TimeStampedModel):
    class Kind(models.TextChoices):
        DAILY = "daily", "Daily practice"
        TOPIC = "topic", "Topic quiz"
        SUBJECT = "subject", "Subject assessment"
        MOCK = "mock", "Full mock examination"
        DIAGNOSTIC = "diagnostic", "Diagnostic assessment"
        LESSON = "lesson", "Lesson check"
        CHALLENGE = "challenge", "Challenge"

    class Mode(models.TextChoices):
        PRACTICE = "practice", "Practice (instant feedback)"
        EXAM = "exam", "Exam simulation (feedback after submit)"

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        SUBMITTED = "submitted"
        EXPIRED = "expired"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    student_exam = models.ForeignKey(
        "examinations.StudentExam", null=True, blank=True, on_delete=models.SET_NULL, related_name="attempts"
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.PRACTICE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL)
    topic = models.ForeignKey("examinations.Topic", null=True, blank=True, on_delete=models.SET_NULL)
    lesson = models.ForeignKey("learning.Lesson", null=True, blank=True, on_delete=models.SET_NULL)
    hearts_enabled = models.BooleanField(default=False)
    hearts_remaining = models.PositiveSmallIntegerField(default=0)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    total_questions = models.PositiveSmallIntegerField(default=0)
    correct_count = models.PositiveSmallIntegerField(default=0)
    score_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    xp_earned = models.PositiveIntegerField(default=0)
    credits_charged = models.PositiveSmallIntegerField(default=0)
    charge_transaction = models.ForeignKey(
        "wallet.CreditTransaction", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    result_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "kind", "-created_at"])]


class DiagnosticAttempt(QuizAttempt):
    """Convenience proxy for diagnostic assessments."""

    class Meta:
        proxy = True


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("questions.Question", on_delete=models.PROTECT)
    order = models.PositiveSmallIntegerField()
    selected_option = models.ForeignKey(
        "questions.QuestionOption", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    is_correct = models.BooleanField(null=True)
    flagged = models.BooleanField(default=False)
    answered_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        unique_together = [("attempt", "question")]


class TopicMastery(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topic_mastery")
    topic = models.ForeignKey("examinations.Topic", on_delete=models.CASCADE, related_name="+")
    subject = models.ForeignKey("examinations.Subject", on_delete=models.CASCADE, related_name="+")
    attempts = models.PositiveIntegerField(default=0)
    correct = models.PositiveIntegerField(default=0)
    mastery = models.FloatField(default=0.0, help_text="0..1 exponentially-weighted accuracy")
    last_practised_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "topic")]
        indexes = [models.Index(fields=["user", "subject"])]
