"""Polite fetching: robots.txt enforced, per-domain rate limit, size cap, honest UA."""
import logging
import time
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

from .discovery import compliance
from .models import Source

logger = logging.getLogger("kwado.research")
MAX_BYTES = 30 * 1024 * 1024
TIMEOUT = 30


class FetchBlocked(Exception):
    """robots.txt or permissions forbid this request. Never retried."""


class RateLimited(Exception):
    """The domain's rate-limit slot wasn't free in time. Retry later."""


@dataclass
class FetchResult:
    url: str
    status: int
    content: bytes
    content_type: str
    backend: str

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    @property
    def is_pdf(self) -> bool:
        return "pdf" in self.content_type.lower() or self.content[:5] == b"%PDF-"


_session = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": settings.RESEARCH_USER_AGENT, "Accept-Language": "en"})
    return _session


def raw_get(url: str, *, allow_status=(200,)) -> tuple[int, str]:
    """Used for robots.txt itself (always permitted to read)."""
    try:
        r = session().get(url, timeout=TIMEOUT)
        return r.status_code, r.text if r.status_code in allow_status else ""
    except requests.RequestException:
        return 0, ""


def _acquire_slot(source: Source, max_wait: float = 90.0):
    """Cross-worker per-domain rate limit using an atomic cache add."""
    key = f"research:rl:{source.domain}"
    deadline = time.monotonic() + max_wait
    while not cache.add(key, 1, timeout=max(1, int(round(source.crawl_delay_seconds)))):
        if time.monotonic() > deadline:
            raise RateLimited(source.domain)
        time.sleep(0.5)


def fetch(source: Source, url: str, *, purpose: str = "discovery") -> FetchResult:
    """Fetch one URL from a source.

    purpose="discovery" — read links/titles only; allowed unless robots/terms forbid.
    purpose="extraction" — store question content; requires source.may_extract.
    """
    if not source.is_active:
        raise FetchBlocked("source inactive")
    if not source.robots_checked_at:
        compliance.check_robots(source, raw_get)
    if not compliance.can_fetch(source, url):
        raise FetchBlocked("robots.txt disallows this URL")
    if purpose == "extraction" and not source.may_extract:
        raise FetchBlocked(f"no permission to extract from {source.domain} ({source.permission_status})")
    if purpose == "discovery" and not compliance.may_crawl_for_discovery(source):
        raise FetchBlocked(f"{source.domain} is {source.permission_status}")

    _acquire_slot(source)
    if settings.FIRECRAWL_API_KEY and purpose == "extraction" and not url.lower().endswith(".pdf"):
        return _fetch_firecrawl(url)
    if settings.RESEARCH_USE_PLAYWRIGHT and not url.lower().endswith(".pdf"):
        return _fetch_playwright(url)
    return _fetch_requests(url)


def _fetch_requests(url: str) -> FetchResult:
    with session().get(url, timeout=TIMEOUT, stream=True, allow_redirects=True) as r:
        chunks, size = [], 0
        for chunk in r.iter_content(64 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("document larger than 30 MB")
            chunks.append(chunk)
        return FetchResult(r.url, r.status_code, b"".join(chunks), r.headers.get("Content-Type", ""), "requests")


def _fetch_playwright(url: str) -> FetchResult:
    """For JavaScript-rendered pages. Requires `pip install playwright` and a Chromium build."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=settings.RESEARCH_USER_AGENT)
        resp = page.goto(url, wait_until="networkidle", timeout=TIMEOUT * 1000)
        html = page.content()
        browser.close()
    return FetchResult(url, resp.status if resp else 0, html.encode(), "text/html", "playwright")


def _fetch_firecrawl(url: str) -> FetchResult:
    from firecrawl import Firecrawl

    doc = Firecrawl(api_key=settings.FIRECRAWL_API_KEY).scrape(url, formats=["html"])
    html = getattr(doc, "html", None) or getattr(doc, "raw_html", None) or ""
    meta = getattr(doc, "metadata", None)
    status = getattr(meta, "status_code", None) or 200
    return FetchResult(url, int(status), html.encode(), "text/html", "firecrawl")
