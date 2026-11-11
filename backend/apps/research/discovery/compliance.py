"""robots.txt and terms-of-use checks.

Automated checks can only make a source MORE restricted (needs_review,
terms_prohibit, robots_disallow). Only a person can mark a source permitted or
openly licensed, by recording a CopyrightPermission.
"""
import re
from urllib import robotparser
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from django.conf import settings
from django.utils import timezone

from ..models import Source

P = Source.Permission
HUMAN_DECIDED = {P.PERMITTED, P.OPEN_LICENSE, P.DENIED}

TERMS_LINK_RE = re.compile(r"terms|tos\b|conditions|legal|copyright|disclaimer|policy", re.I)
# Phrases that indicate copying or automated access is not allowed.
PROHIBIT_PATTERNS = [
    r"(may|must|shall) not (copy|reproduce|republish|redistribute|scrape|crawl)",
    r"(scraping|crawling|harvesting|data mining)[^.]{0,80}(prohibit|not (allowed|permitted))",
    r"(prohibit|not (allowed|permitted))[^.]{0,80}(scraping|crawling|robots?|spiders?|automated)",
    r"without (our |the )?(prior )?(express )?written (permission|consent)",
    r"(reproduction|redistribution)[^.]{0,60}(strictly )?prohibited",
]
OPEN_LICENSE_RE = re.compile(r"creativecommons\.org/licenses/([a-z\-]+)/([\d.]+)", re.I)


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _parser(source: Source) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser()
    rp.parse((source.robots_txt or "").splitlines())
    return rp


def can_fetch(source: Source, url: str) -> bool:
    """robots.txt decision for our user agent. No robots.txt (empty) means allowed."""
    if not source.robots_checked_at:
        return False  # must check robots first
    return _parser(source).can_fetch(settings.RESEARCH_USER_AGENT, url)


def check_robots(source: Source, http_get) -> Source:
    """Fetch and store robots.txt. `http_get(url) -> (status, text)` is injected for testability."""
    base = source.homepage or f"https://{source.domain}/"
    status, text = http_get(urljoin(base, "/robots.txt"))
    if status in (401, 403):
        # Per RFC 9309, an access-restricted robots.txt means full disallow.
        text = "User-agent: *\nDisallow: /\n"
    elif status >= 400 or status == 0:
        text = ""  # no robots.txt → everything allowed
    source.robots_txt = (text or "")[:100_000]
    source.robots_checked_at = timezone.now()
    rp = _parser(source)
    delay = rp.crawl_delay(settings.RESEARCH_USER_AGENT)
    source.crawl_delay_seconds = max(float(delay or 0), settings.RESEARCH_DEFAULT_CRAWL_DELAY)
    if not rp.can_fetch(settings.RESEARCH_USER_AGENT, base) and source.permission_status not in HUMAN_DECIDED:
        source.permission_status = P.ROBOTS_DISALLOW
    source.save(update_fields=["robots_txt", "robots_checked_at", "crawl_delay_seconds", "permission_status", "updated_at"])
    return source


def find_terms_url(homepage_html: str, base_url: str) -> str:
    soup = BeautifulSoup(homepage_html or "", "html.parser")
    best = ""
    for a in soup.find_all("a", href=True):
        label = f"{a.get_text(' ', strip=True)} {a['href']}"
        if TERMS_LINK_RE.search(label):
            href = urljoin(base_url, a["href"])
            if domain_of(href) == domain_of(base_url):
                if re.search(r"terms|conditions|tos\b", label, re.I):
                    return href
                best = best or href
    return best


def scan_terms(text: str) -> tuple[list[str], str]:
    """Return (flags, licence) found in terms text."""
    flags = []
    low = re.sub(r"\s+", " ", text.lower())
    for pat in PROHIBIT_PATTERNS:
        m = re.search(pat, low)
        if m:
            flags.append(m.group(0)[:160])
    lic = ""
    m = OPEN_LICENSE_RE.search(text)
    if m:
        lic = f"CC {m.group(1).upper()} {m.group(2)}"
    return flags, lic


def apply_terms(source: Source, terms_url: str, terms_text: str) -> Source:
    flags, lic = scan_terms(terms_text or "")
    source.terms_url = terms_url or ""
    source.terms_checked_at = timezone.now()
    source.terms_flags = flags
    if lic:
        source.license_name = lic
    if source.permission_status not in HUMAN_DECIDED | {P.ROBOTS_DISALLOW}:
        # A licence is only a hint: a person must confirm it allows our use (NC/ND variants matter).
        source.permission_status = P.TERMS_PROHIBIT if flags else P.NEEDS_REVIEW
    source.save(update_fields=["terms_url", "terms_checked_at", "terms_flags", "license_name", "permission_status", "updated_at"])
    return source


def may_crawl_for_discovery(source: Source) -> bool:
    """Following links to find documents (metadata only, like a search engine)."""
    return source.is_active and source.permission_status not in (P.ROBOTS_DISALLOW, P.TERMS_PROHIBIT, P.DENIED)
