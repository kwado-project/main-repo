from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class Subject(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    icon = models.CharField(max_length=40, default="book-open", help_text="Lucide icon name")
    color = models.CharField(max_length=9, default="#16A34A")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Topic(TimeStampedModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subtopics"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    weight = models.PositiveSmallIntegerField(default=1, help_text="Relative exam importance 1-5")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["subject", "order", "name"]
        unique_together = [("subject", "slug")]

    def __str__(self):
        return f"{self.subject.name} · {self.name}"


class Examination(TimeStampedModel):
    name = models.CharField(max_length=80, unique=True)
    code = models.SlugField(max_length=30, unique=True)
    full_name = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=9, default="#16A34A")
    min_subjects = models.PositiveSmallIntegerField(default=4)
    max_subjects = models.PositiveSmallIntegerField(default=4)
    questions_per_subject_mock = models.PositiveSmallIntegerField(default=40)
    mock_duration_minutes = models.PositiveSmallIntegerField(default=120)
    rules_note = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    subjects = models.ManyToManyField(Subject, through="ExamSubject", related_name="examinations")

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def validate_subject_selection(self, subject_ids):
        subject_ids = set(subject_ids)
        allowed = set(self.exam_subjects.values_list("subject_id", flat=True))
        compulsory = set(self.exam_subjects.filter(is_compulsory=True).values_list("subject_id", flat=True))
        errors = []
        if not subject_ids <= allowed:
            errors.append("Some selected subjects are not offered for this examination.")
        if not compulsory <= subject_ids:
            names = Subject.objects.filter(id__in=compulsory - subject_ids).values_list("name", flat=True)
            errors.append(f"{', '.join(names)} is compulsory for {self.name}.")
        if not (self.min_subjects <= len(subject_ids) <= self.max_subjects):
            if self.min_subjects == self.max_subjects:
                errors.append(f"{self.name} requires exactly {self.min_subjects} subjects.")
            else:
                errors.append(f"Choose between {self.min_subjects} and {self.max_subjects} subjects for {self.name}.")
        if errors:
            raise ValidationError(errors)


class ExamSubject(models.Model):
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name="exam_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="exam_links")
    is_compulsory = models.BooleanField(default=False)

    class Meta:
        unique_together = [("examination", "subject")]


class StudentExam(TimeStampedModel):
    """A student's preparation profile for one examination."""

    class OnboardingStep(models.TextChoices):
        DATE = "date"
        SUBJECTS = "subjects"
        STUDY_TIME = "study_time"
        DIAGNOSTIC = "diagnostic"
        ROADMAP = "roadmap"
        DONE = "done"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_exams")
    examination = models.ForeignKey(Examination, on_delete=models.PROTECT, related_name="student_exams")
    exam_date = models.DateField(null=True, blank=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="+")
    daily_minutes = models.PositiveSmallIntegerField(default=45)
    study_days = models.JSONField(default=list, blank=True, help_text="0=Mon … 6=Sun")
    target_score = models.PositiveSmallIntegerField(null=True, blank=True)
    onboarding_step = models.CharField(max_length=12, choices=OnboardingStep.choices, default=OnboardingStep.DATE)
    is_archived = models.BooleanField(default=False)

    class Meta:
        unique_together = [("user", "examination")]
        indexes = [models.Index(fields=["user", "is_archived"])]

    def __str__(self):
        return f"{self.user} · {self.examination}"
