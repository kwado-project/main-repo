"""Durable, idempotent job records so the pipeline can resume and never repeats finished work."""
import traceback
from contextlib import contextmanager
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import ExtractionJob

J = ExtractionJob.Status
MAX_ATTEMPTS = 3
STALE_AFTER = timedelta(minutes=30)


class AlreadyDone(Exception):
    pass


def claim(kind: str, key: str, **fk) -> ExtractionJob | None:
    """Atomically claim a job. Returns None if it already succeeded, is running, or is exhausted."""
    try:
        with transaction.atomic():
            job, _ = ExtractionJob.objects.get_or_create(idempotency_key=key, defaults={"kind": kind, **fk})
    except IntegrityError:
        job = ExtractionJob.objects.get(idempotency_key=key)
    with transaction.atomic():
        job = ExtractionJob.objects.select_for_update().get(pk=job.pk)
        if job.status in (J.SUCCEEDED, J.SKIPPED, J.RUNNING):
            return None
        if job.status == J.FAILED and job.attempts >= MAX_ATTEMPTS:
            return None
        job.status = J.RUNNING
        job.attempts += 1
        job.started_at = timezone.now()
        job.error = ""
        job.save(update_fields=["status", "attempts", "started_at", "error", "updated_at"])
    return job


def finish(job: ExtractionJob, status: str, result: dict | None = None, error: str = ""):
    job.status = status
    job.finished_at = timezone.now()
    job.result = result or {}
    job.error = error[:5000]
    job.save(update_fields=["status", "finished_at", "result", "error", "updated_at"])


@contextmanager
def run(kind: str, key: str, **fk):
    """with jobs.run(...) as job: — yields None if there's nothing to do."""
    job = claim(kind, key, **fk)
    if job is None:
        yield None
        return
    holder = {"result": {}, "status": J.SUCCEEDED}
    try:
        yield holder
    except Exception as e:  # noqa: BLE001
        finish(job, J.FAILED, holder.get("result"), f"{type(e).__name__}: {e}\n{traceback.format_exc()[-3000:]}")
        raise
    else:
        finish(job, holder["status"], holder["result"])


def resume_stale() -> int:
    """Jobs left RUNNING by a crashed worker go back to FAILED (retryable)."""
    cutoff = timezone.now() - STALE_AFTER
    return ExtractionJob.objects.filter(status=J.RUNNING, started_at__lt=cutoff).update(
        status=J.FAILED, error="Interrupted (worker stopped); will be retried.", finished_at=timezone.now())
