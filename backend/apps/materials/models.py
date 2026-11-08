from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.core.models import TimeStampedModel


class StudyMaterial(TimeStampedModel):
    class Status(models.TextChoices):
        UPLOADED = "uploaded"
        PROCESSING = "processing"
        READY = "ready"
        FAILED = "failed"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private to owner"
        APPROVED_SOURCE = "approved", "Approved platform source"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="materials"
    )
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    student_exam = models.ForeignKey("examinations.StudentExam", null=True, blank=True, on_delete=models.SET_NULL)
    examination = models.ForeignKey("examinations.Examination", null=True, blank=True, on_delete=models.SET_NULL)
    subject = models.ForeignKey("examinations.Subject", null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=200)
    filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=300, unique=True)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPLOADED)
    extracted_chars = models.PositiveIntegerField(default=0)
    analysis = models.TextField(blank=True)
    analysis_charged = models.BooleanField(default=False)
    error = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "-created_at"])]


class MaterialChunk(models.Model):
    material = models.ForeignKey(StudyMaterial, on_delete=models.CASCADE, related_name="chunks")
    index = models.PositiveIntegerField()
    text = models.TextField()
    embedding = VectorField(dimensions=settings.EMBEDDING_DIMENSIONS)

    class Meta:
        unique_together = [("material", "index")]
        indexes = [
            HnswIndex(name="chunk_embedding_hnsw", fields=["embedding"], m=16, ef_construction=64,
                      opclasses=["vector_cosine_ops"])
        ]
