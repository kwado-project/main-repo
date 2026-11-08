from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        STREAK = "streak"
        ACHIEVEMENT = "achievement"
        PAYMENT = "payment"
        REFERRAL = "referral"
        ROADMAP = "roadmap"
        SYSTEM = "system"
        MATERIAL = "material"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=255, blank=True)
    link = models.CharField(max_length=200, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at", "-created_at"])]


def notify(user, kind, title, body="", link=""):
    return Notification.objects.create(user=user, kind=kind, title=title, body=body, link=link)
