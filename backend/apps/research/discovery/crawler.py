"""Source registry updates and same-site link discovery (metadata only)."""
import logging
import re
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup
from django.conf import settings

from apps.examinations.models import Subject

from .. import fetch
from ..models import Source, SourceDocument
from . import compliance
from .classify import classify, is_relevant

logger = logging.getLogger("kwado.research")

FOLLOW_RE = re.compile(r"past|question|jamb|utme|answer|subject|exam|\b(19|20)\d{2}\b|pdf|download", re.I)
SKIP_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".rar", ".mp3", ".mp4", ".doc", ".docx", ".ppt", ".css", ".js")


def get_or_create_source(url: str, via: str, name: str = "") -> Source:
    domain = compliance.domain_of(url)
    p = urlparse(url)
    src, _ = Source.objects.get_or_create(
        domain=domain, defaults={"homepage": f"{p.scheme or 'https'}://{p.netloc}/", "discovered_via": via, "name": name[:200]})
    return src


def subject_for(slug: str):
    return Subject.objects.filter(slug=slug).first() if slug else None


def record_document(source: Source, url: str, *, title="", snippet="", via="", query="", depth=0) -> SourceDocument | None:
    """Upsert a candidate document if it looks like JAMB past questions. Metadata only."""
    url = urldefrag(url)[0]
    c = classify(url, title, snippet, settings.RESEARCH_YEAR_FROM, settings.RESEARCH_YEAR_TO)
    if not is_relevant(c):
        return None
    kind = SourceDocument.Kind.PDF if url.lower().split("?")[0].endswith(".pdf") else SourceDocument.Kind.HTML
    doc, created = SourceDocument.objects.get_or_create(url=url, defaults={
        "source": source, "kind": kind, "title": title[:500], "snippet": snippet[:2000],
        "examination_guess": c.exam, "subject": subject_for(c.subject_slug), "year": c.year,
        "classification_confidence": c.confidence, "discovered_via": via, "discovery_query": query[:300], "depth": depth,
    })
    if not created and c.confidence > doc.classification_confidence:
        doc.title = doc.title or title[:500]
        doc.subject = doc.subject or subject_for(c.subject_slug)
        doc.year = doc.year or c.year
        doc.classification_confidence = c.confidence
        doc.save(update_fields=["title", "subject", "year", "classification_confidence", "updated_at"])
    _note_coverage(source, c)
    return doc


def _note_coverage(source: Source, c):
    changed = False
    if c.subject_slug and c.subject_slug not in source.subjects_seen:
        source.subjects_seen = sorted(set(source.subjects_seen) | {c.subject_slug})
        changed = True
    if c.year and c.year not in source.years_seen:
        source.years_seen = sorted(set(source.years_seen) | {c.year})
        changed = True
    if changed:
        source.save(update_fields=["subjects_seen", "years_seen", "updated_at"])


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(base_url, a["href"].strip()))[0]
        if href.startswith(("http://", "https://")):
            out.append((href, a.get_text(" ", strip=True)[:300]))
    return out


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return (soup.title.get_text(strip=True) if soup.title else "")[:500]


def check_compliance(source: Source) -> Source:
    """robots.txt, then the terms page (via the homepage)."""
    compliance.check_robots(source, fetch.raw_get)
    if source.permission_status == Source.Permission.ROBOTS_DISALLOW or source.terms_checked_at:
        return source
    try:
        home = fetch.fetch(source, source.homepage or f"https://{source.domain}/", purpose="discovery")
        terms_url = compliance.find_terms_url(home.text, home.url)
        terms_text = ""
        if terms_url and compliance.can_fetch(source, terms_url):
            terms_text = BeautifulSoup(fetch.fetch(source, terms_url, purpose="discovery").text, "html.parser").get_text(" ")
        compliance.apply_terms(source, terms_url, terms_text)
    except (fetch.FetchBlocked, fetch.RateLimited):
        raise
    except Exception as e:  # noqa: BLE001
        logger.info("terms check failed for %s: %s", source.domain, e)
        compliance.apply_terms(source, "", "")
    return source


def crawl(source: Source, start_urls: list[str], max_depth: int | None = None, max_pages: int | None = None) -> dict:
    """Breadth-first, same-domain discovery of past-question documents. Stores metadata only."""
    max_depth = settings.RESEARCH_MAX_CRAWL_DEPTH if max_depth is None else max_depth
    max_pages = max_pages or settings.RESEARCH_MAX_PAGES_PER_SOURCE
    if not compliance.may_crawl_for_discovery(source):
        return {"skipped": source.permission_status}
    queue, seen = deque((u, 0) for u in start_urls), set()
    pages = found = blocked = 0
    while queue and pages < max_pages:
        url, depth = queue.popleft()
        if url in seen or url.lower().split("?")[0].endswith(SKIP_EXT + (".pdf",)):
            continue
        seen.add(url)
        try:
            res = fetch.fetch(source, url, purpose="discovery")
        except fetch.FetchBlocked:
            blocked += 1
            continue
        except fetch.RateLimited:
            break
        except Exception as e:  # noqa: BLE001
            logger.info("crawl fetch failed %s: %s", url, e)
            continue
        pages += 1
        if res.status != 200 or "html" not in res.content_type.lower():
            continue
        if record_document(source, res.url, title=page_title(res.text), via="crawl", depth=depth):
            found += 1
        for href, anchor in extract_links(res.text, res.url):
            if compliance.domain_of(href) != source.domain:
                continue
            if record_document(source, href, title=anchor, via="crawl", depth=depth + 1):
                found += 1
            if depth < max_depth and href not in seen and FOLLOW_RE.search(f"{href} {anchor}"):
                queue.append((href, depth + 1))
    return {"pages_crawled": pages, "documents_recorded": found, "blocked_by_robots": blocked}
