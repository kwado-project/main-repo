"""Pipeline steps. Each is idempotent and recorded as an ExtractionJob."""
import logging

from django.conf import settings
from django.utils import timezone

from . import fetch, jobs, matrix
from .discovery import crawler, search
from .discovery.queries import queries_for
from .models import ExtractionJob, ResearchTarget, Source, SourceDocument

logger = logging.getLogger("kwado.research")
K = ExtractionJob.Kind


# --------------------------------------------------------------------- discovery
def discover_target(target: ResearchTarget) -> dict:
    """Search for one subject/year cell and record candidate documents (metadata only)."""
    attempt = target.search_attempts + 1
    key = f"discover:{target.pk}:{attempt}"
    with jobs.run(K.DISCOVER, key, target=target) as job:
        if job is None:
            return {"skipped": "already done"}
        ResearchTarget.objects.filter(pk=target.pk).update(status=ResearchTarget.Status.SEARCHING)
        providers = search.available_providers()
        result = {"providers": [p.name for p in providers], "queries": 0, "hits": 0, "recorded": 0, "errors": []}
        if not providers:
            result["note"] = "No search provider configured; only seed sites are crawled."
        for q in queries_for(target.subject.name, target.subject.slug, target.exam_year.year):
            hits, errors = search.search_all(q)
            result["queries"] += 1
            result["hits"] += len(hits)
            result["errors"] += errors
            for h in hits:
                src = crawler.get_or_create_source(h.url, h.provider)
                if crawler.record_document(src, h.url, title=h.title, snippet=h.snippet, via=h.provider, query=q):
                    result["recorded"] += 1
        target.search_attempts = attempt
        target.last_searched_at = timezone.now()
        target.save(update_fields=["search_attempts", "last_searched_at", "updated_at"])
        target.status = ResearchTarget.Status.MISSING
        matrix.refresh_target(target)
        job["result"] = result
        return result


def check_source(source: Source, force: bool = False) -> dict:
    """robots.txt + terms check for one source (re-run at most daily unless forced)."""
    day = timezone.localdate().isoformat()
    key = f"compliance:{source.pk}:{day}{':force' if force else ''}"
    with jobs.run(K.COMPLIANCE, key, source=source) as job:
        if job is None:
            return {"skipped": "already checked today"}
        try:
            crawler.check_compliance(source)
        except fetch.RateLimited:
            job["status"] = ExtractionJob.Status.FAILED
        source.refresh_from_db()
        job["result"] = {"permission_status": source.permission_status, "terms_flags": source.terms_flags,
                         "crawl_delay": source.crawl_delay_seconds}
        return job["result"]


def crawl_source(source: Source, start_urls: list[str] | None = None) -> dict:
    """Follow same-site links from the homepage (or given URLs) to find more documents."""
    week = timezone.localdate().isocalendar()
    key = f"crawl:{source.pk}:{week[0]}-W{week[1]}"
    with jobs.run(K.CRAWL, key, source=source) as job:
        if job is None:
            return {"skipped": "crawled this week"}
        if not source.robots_checked_at:
            check_source(source)
            source.refresh_from_db()
        starts = start_urls or [source.homepage or f"https://{source.domain}/"]
        job["result"] = crawler.crawl(source, starts)
        return job["result"]


def add_seed(url: str, name: str = "") -> Source:
    src = crawler.get_or_create_source(url, "seed", name)
    if not src.is_seed:
        src.is_seed = True
        src.save(update_fields=["is_seed", "updated_at"])
    return src
