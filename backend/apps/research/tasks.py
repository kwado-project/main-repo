"""Celery tasks (queue: "research"). Run a dedicated worker: celery -A config worker -Q research."""
from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from . import pipeline
from .models import ResearchTarget, Source, SourceDocument

CYCLE_LOCK = "research:cycle-lock"


@shared_task(bind=True, soft_time_limit=60 * 55, time_limit=60 * 60)
def research_cycle(self, scheduled: bool = False, **kwargs):
    """One autonomous pass. A lock prevents two cycles running at once."""
    if scheduled and not settings.RESEARCH_AUTORUN:
        return {"skipped": "RESEARCH_AUTORUN is off"}
    if not cache.add(CYCLE_LOCK, self.request.id or "manual", timeout=60 * 60):
        return {"skipped": "another cycle is running"}
    try:
        return pipeline.run_cycle(**kwargs)
    finally:
        cache.delete(CYCLE_LOCK)


@shared_task
def discover_target_task(target_id: int):
    return pipeline.discover_target(ResearchTarget.objects.select_related("exam_year", "subject").get(pk=target_id))


@shared_task
def check_source_task(source_id: int, force: bool = False):
    return pipeline.check_source(Source.objects.get(pk=source_id), force=force)


@shared_task
def crawl_source_task(source_id: int):
    return pipeline.crawl_source(Source.objects.get(pk=source_id))


@shared_task(autoretry_for=(Exception,), retry_backoff=60, max_retries=3)
def extract_document_task(document_id: int, force: bool = False):
    return pipeline.extract_document(SourceDocument.objects.select_related("source").get(pk=document_id), force=force)


@shared_task
def verify_pending_task(limit: int = 500):
    return pipeline.verify_pending(limit)
