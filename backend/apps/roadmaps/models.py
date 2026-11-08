from django.db import models

from apps.core.models import TimeStampedModel


class Roadmap(TimeStampedModel):
    student_exam = models.ForeignKey("examinations.StudentExam", on_delete=models.CASCADE, related_name="roadmaps")
    is_current = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    summary = models.TextField(blank=True)
    ai_summary = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    inputs = models.JSONField(default=dict, blank=True)
    last_adapted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["student_exam", "is_current"])]


class LearningTask(TimeStampedModel):
    class Kind(models.TextChoices):
        LESSON = "lesson", "Lesson"
        PRACTICE = "practice", "Practice"
        REVISION = "revision", "Revision"
        MOCK = "mock", "Mock exam"
        DIAGNOSTIC = "diagnostic", "Diagnostic"

    class Priority(models.TextChoices):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

    class Status(models.TextChoices):
        PENDING = "pending"
        COMPLETED = "completed"
        SKIPPED = "skipped"

    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="tasks")
    date = models.DateField(db_index=True)
    order = models.PositiveSmallIntegerField(default=0)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    title = models.CharField(max_length=200)
    description = models.CharField(max_length=255, blank=True)
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL)
    topic = models.ForeignKey("examinations.Topic", null=True, blank=True, on_delete=models.SET_NULL)
    lesson = models.ForeignKey("learning.Lesson", null=True, blank=True, on_delete=models.SET_NULL)
    minutes = models.PositiveSmallIntegerField(default=20)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["date", "order"]
