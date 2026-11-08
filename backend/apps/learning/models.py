from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Lesson(TimeStampedModel):
    topic = models.ForeignKey("examinations.Topic", on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    objective = models.CharField(max_length=255)
    estimated_minutes = models.PositiveSmallIntegerField(default=8)
    content = models.JSONField(
        default=list,
        help_text='Ordered blocks: {"type": "text|example|tip|formula|check", ...}',
    )
    xp_reward = models.PositiveSmallIntegerField(default=20)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["topic", "order"]
        unique_together = [("topic", "slug")]

    def __str__(self):
        return self.title


class LessonProgress(TimeStampedModel):
    class Status(models.TextChoices):
        STARTED = "started"
        COMPLETED = "completed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="+")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.STARTED)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "lesson")]


class LearningPath(TimeStampedModel):
    examination = models.ForeignKey(
        "examinations.Examination", null=True, blank=True, on_delete=models.CASCADE, related_name="learning_paths"
    )
    subject = models.ForeignKey("examinations.Subject", on_delete=models.CASCADE, related_name="learning_paths")
    title = models.CharField(max_length=160)
    is_published = models.BooleanField(default=True)

    class Meta:
        unique_together = [("examination", "subject")]

    def __str__(self):
        return self.title


class LearningPathNode(models.Model):
    class Kind(models.TextChoices):
        LESSON = "lesson", "Lesson"
        CHALLENGE = "challenge", "Topic challenge"
        BOSS = "boss", "Boss challenge"

    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="nodes")
    order = models.PositiveIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    title = models.CharField(max_length=160)
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE)
    topic = models.ForeignKey("examinations.Topic", null=True, blank=True, on_delete=models.CASCADE)
    pass_mark = models.PositiveSmallIntegerField(default=70)

    class Meta:
        ordering = ["path", "order"]
        unique_together = [("path", "order")]


class NodeCompletion(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    node = models.ForeignKey(LearningPathNode, on_delete=models.CASCADE, related_name="+")
    best_score = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [("user", "node")]
