from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Passage(TimeStampedModel):
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    source = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.title or self.body[:60]


class Question(TimeStampedModel):
    """A question in the bank.

    Workflow: draft → validated → answer_verified → in_review → published.
    Only `published` questions are served to students, and publishing requires
    a human-verified AnswerKey. AI-generated questions start as drafts and can
    never skip human answer verification.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Imported / draft"
        VALIDATED = "validated", "Validated"
        ANSWER_VERIFIED = "answer_verified", "Answer verified"
        IN_REVIEW = "in_review", "In review"
        PUBLISHED = "published", "Published"
        REJECTED = "rejected", "Rejected"

    class Difficulty(models.IntegerChoices):
        EASY = 1, "Easy"
        MEDIUM = 2, "Medium"
        HARD = 3, "Hard"

    examination = models.ForeignKey(
        "examinations.Examination", null=True, blank=True, on_delete=models.SET_NULL, related_name="questions"
    )
    subject = models.ForeignKey("examinations.Subject", on_delete=models.PROTECT, related_name="questions")
    topic = models.ForeignKey(
        "examinations.Topic", null=True, blank=True, on_delete=models.SET_NULL, related_name="questions"
    )
    subtopic = models.CharField(max_length=120, blank=True)
    passage = models.ForeignKey(Passage, null=True, blank=True, on_delete=models.SET_NULL, related_name="questions")
    text = models.TextField(help_text="Supports Markdown and LaTeX ($…$ inline, $$…$$ block)")
    image_url = models.URLField(max_length=500, blank=True)
    table_data = models.JSONField(null=True, blank=True)
    explanation = models.TextField(blank=True)
    solution_steps = models.JSONField(default=list, blank=True)
    difficulty = models.PositiveSmallIntegerField(choices=Difficulty.choices, default=Difficulty.MEDIUM)
    exam_year = models.PositiveSmallIntegerField(null=True, blank=True)
    source = models.CharField(max_length=200, blank=True, help_text="Authorised source / licence")
    is_official_past_question = models.BooleanField(default=False)
    is_ai_generated = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    review_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["subject", "status", "topic"]),
            models.Index(fields=["examination", "subject", "status"]),
        ]

    def __str__(self):
        return self.text[:80]


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=2)
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]
        unique_together = [("question", "label")]

    def __str__(self):
        return f"{self.label}. {self.text[:40]}"


class AnswerKey(TimeStampedModel):
    """The single source of truth for marking. Never set by AI."""

    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="answer_key")
    correct_option = models.ForeignKey(QuestionOption, on_delete=models.PROTECT, related_name="+")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_source = models.CharField(max_length=200, blank=True)

    @property
    def is_verified(self):
        return bool(self.verified_by_id and self.verified_at)
