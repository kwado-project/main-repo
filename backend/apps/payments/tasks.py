from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Payment


@shared_task
def expire_stale_payments():
    cutoff = timezone.now() - timedelta(hours=24)
    Payment.objects.filter(status=Payment.Status.PENDING, created_at__lt=cutoff).update(
        status=Payment.Status.ABANDONED
    )
