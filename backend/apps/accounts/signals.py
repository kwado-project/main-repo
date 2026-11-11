from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User, dispatch_uid="accounts.ensure_account_records")
def create_account_records(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        from .services import ensure_account_records
        with transaction.atomic():
            ensure_account_records(instance)
