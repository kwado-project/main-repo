import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("kwado")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "streak-reminders": {"task": "apps.notifications.tasks.send_streak_reminders", "schedule": crontab(hour=18, minute=7)},
    "expire-stale-payments": {"task": "apps.payments.tasks.expire_stale_payments", "schedule": crontab(minute="*/30")},
    "purge-expired-otps": {"task": "apps.accounts.tasks.purge_expired_otps", "schedule": crontab(hour=3, minute=13)},
}
