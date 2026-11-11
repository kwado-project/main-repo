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


# --------------------------------------------------------------------- extraction
def extract_document(doc: SourceDocument, force: bool = False) -> dict:
    """Fetch one permitted document, parse it and stage its questions. Never runs twice for the same content."""
    import hashlib

    from apps.core.services import storage

    from .extraction import html as html_ex
    from .extraction import pdf as pdf_ex
    from .extraction.parser import parse_text
    from .extraction.structure import save_parsed

    key = f"extract:{doc.pk}" + (f":force:{timezone.now():%Y%m%d%H%M}" if force else "")
    with jobs.run(K.EXTRACT, key, document=doc, source=doc.source) as job:
        if job is None:
            return {"skipped": "already extracted"}
        source = doc.source
        if not source.may_extract:
            doc.status, doc.status_reason = SourceDocument.Status.BLOCKED, f"source is {source.permission_status}"
            doc.save(update_fields=["status", "status_reason", "updated_at"])
            job["status"] = ExtractionJob.Status.SKIPPED
            job["result"] = {"blocked": doc.status_reason}
            return job["result"]
        doc.attempts += 1
        try:
            res = fetch.fetch(source, doc.url, purpose="extraction")
        except fetch.FetchBlocked as e:
            doc.status, doc.status_reason = SourceDocument.Status.BLOCKED, str(e)[:255]
            doc.save(update_fields=["status", "status_reason", "attempts", "updated_at"])
            job["status"] = ExtractionJob.Status.SKIPPED
            job["result"] = {"blocked": str(e)}
            return job["result"]
        doc.http_status, doc.content_type, doc.fetch_backend = res.status, res.content_type[:120], res.backend
        doc.fetched_at = timezone.now()
        if res.status != 200 or not res.content:
            doc.status, doc.status_reason = SourceDocument.Status.FAILED, f"HTTP {res.status}"
            doc.save()
            raise RuntimeError(f"HTTP {res.status} for {doc.url}")
        sha = hashlib.sha256(res.content).hexdigest()
        doc.content_hash = sha
        twin = SourceDocument.objects.filter(content_hash=sha, status=SourceDocument.Status.EXTRACTED).exclude(pk=doc.pk).first()
        if twin:
            doc.status, doc.status_reason = SourceDocument.Status.SKIPPED, f"identical content to document {twin.pk}"
            doc.save()
            job["result"] = {"duplicate_of_document": twin.pk}
            return job["result"]
        ext = "pdf" if res.is_pdf else "html"
        doc.kind = SourceDocument.Kind.PDF if res.is_pdf else SourceDocument.Kind.HTML
        doc.storage_key = f"research/raw/{source.domain}/{sha}.{ext}"
        storage.put_object(doc.storage_key, res.content, "application/pdf" if res.is_pdf else "text/html")
        warnings = []
        if res.is_pdf:
            pdf = pdf_ex.pdf_to_text(res.content)
            text, method, title, warnings = pdf.text, pdf.method, doc.title, pdf.warnings
        else:
            text, title = html_ex.html_to_text(res.text, res.url)
            method = "html"
        paper = parse_text(text)
        doc.title = doc.title or (title or "")[:500]
        result = save_parsed(doc, paper, method, header_text=title or "")
        result["warnings"] = warnings + result["warnings"]
        if res.is_pdf and pdf.images:
            result["images_stored"] = _store_pdf_diagrams(doc, pdf.images, sha)
        doc.status = SourceDocument.Status.EXTRACTED if paper.questions else SourceDocument.Status.NO_QUESTIONS
        doc.status_reason = "" if paper.questions else "no numbered questions with options found"
        doc.save()
        job["result"] = {**result, "method": method, "questions_parsed": len(paper.questions)}
        return job["result"]


def _store_pdf_diagrams(doc: SourceDocument, images, sha: str) -> int:
    """Attach images from a PDF page to that page's questions that mention a diagram."""
    from apps.core.services import storage

    from .models import PastQuestion

    by_page = {}
    for page, data, ext in images:
        by_page.setdefault(page, []).append((data, ext))
    stored = 0
    for q in PastQuestion.objects.filter(document=doc, has_diagram=True, page_number__in=list(by_page)):
        refs = list(q.image_refs)
        for i, (data, ext) in enumerate(by_page[q.page_number][:4]):
            key = f"research/img/{sha[:16]}-p{q.page_number}-{i}.{ext}"
            if key not in refs:
                storage.put_object(key, data, f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}")
                refs.append(key)
                stored += 1
        PastQuestion.objects.filter(pk=q.pk).update(image_refs=refs)
    return stored
