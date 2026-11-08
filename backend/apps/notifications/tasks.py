from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.core.services.email import send_email
from apps.gamification.models import Streak

from .models import notify


@shared_task
def send_streak_reminders():
    """Evening nudge for students whose streak will break tonight. Batched by id."""
    yesterday = timezone.localdate() - timedelta(days=1)
    qs = (Streak.objects.filter(last_active_date=yesterday, current__gte=2, user__is_active=True,
                                user__profile__notify_streak=True)
          .select_related("user", "user__profile").order_by("id"))
    last_id = 0
    while True:
        batch = list(qs.filter(id__gt=last_id)[:1000])
        if not batch:
            break
        for s in batch:
            notify(s.user, "streak", f"Keep your {s.current}-day streak alive",
                   "One short lesson or quiz today keeps it going.", "/app")
            if s.user.profile.notify_email_reminders:
                send_email(s.user.email, f"Your {s.current}-day Kwado streak ends tonight",
                           "A 5-minute practice keeps it alive. Open Kwado AI to continue.")
        last_id = batch[-1].id
