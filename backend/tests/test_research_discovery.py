"""Stage 1: matrix, classification, compliance, discovery and jobs. No real network."""
import pytest
from django.test import override_settings

from apps.research import fetch, jobs, matrix, pipeline
from apps.research.discovery import classify as cl
from apps.research.discovery import compliance, search
from apps.research.models import ExtractionJob, ResearchTarget, Source, SourceDocument

pytestmark = pytest.mark.django_db

ROBOTS_OK = "User-agent: *\nDisallow: /admin/\nCrawl-delay: 2\n"
TERMS_STRICT = "<html><body><h1>Terms</h1><p>You may not copy, reproduce or republish any content without our prior written permission. Scraping and automated access are prohibited.</p></body></html>"
TERMS_LOOSE = "<html><body><h1>Terms of use</h1><p>Be nice. Content is provided for students.</p></body></html>"


class FakeWeb:
    """In-memory website: url -> (status, content_type, body)."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def raw_get(self, url, allow_status=(200,)):
        self.requested.append(url)
        status, _, body = self.pages.get(url, (404, "text/plain", ""))
        return status, body if status in allow_status else ""

    def fetch(self, url):
        self.requested.append(url)
        status, ctype, body = self.pages.get(url, (404, "text/html", ""))
        return fetch.FetchResult(url, status, body.encode() if isinstance(body, str) else body, ctype, "fake")


@pytest.fixture
def web(monkeypatch):
    def install(pages):
        w = FakeWeb(pages)
        monkeypatch.setattr(fetch, "raw_get", w.raw_get)
        monkeypatch.setattr(fetch, "_fetch_requests", w.fetch)
        monkeypatch.setattr(fetch, "_acquire_slot", lambda source, max_wait=90.0: None)
        return w
    return install


# ------------------------------------------------------------------ classification
@pytest.mark.parametrize("url,title,exam,subject,year", [
    ("https://x.ng/jamb-mathematics-past-questions-2005.pdf", "", "jamb", "mathematics", 2005),
    ("https://x.ng/pq/123", "JAMB Use of English Past Questions 2014 with Answers", "jamb", "english-language", 2014),
    ("https://x.ng/utme/principles-of-accounts/2019", "", "jamb", "financial-accounting", 2019),
    ("https://x.ng/crk-2011", "UTME CRK 2011 questions", "jamb", "christian-religious-studies", 2011),
    ("https://x.ng/waec-biology-2010", "WAEC Biology 2010 past questions", "waec", "biology", 2010),
    ("https://x.ng/post-utme-unilag-physics-2018", "Post UTME physics 2018", "post-utme", "physics", 2018),
])
def test_classify(url, title, exam, subject, year):
    c = cl.classify(url, title)
    assert (c.exam, c.subject_slug, c.year) == (exam, subject, year)


def test_relevance_rejects_other_exams_and_noise():
    assert cl.is_relevant(cl.classify("https://x.ng/jamb-physics-past-questions-2020.pdf"))
    assert not cl.is_relevant(cl.classify("https://x.ng/waec-physics-past-questions-2020.pdf"))
    assert not cl.is_relevant(cl.classify("https://x.ng/about-us"))


# ------------------------------------------------------------------ matrix
def test_matrix_covers_every_jamb_subject_and_year(seeded):
    out = matrix.ensure_matrix("jamb", 2000, 2026)
    subjects = out["subjects"]
    assert out["total_targets"] == subjects * 27
    assert matrix.ensure_matrix("jamb", 2000, 2026)["created_targets"] == 0  # idempotent
    assert matrix.status_counts()["missing"] == subjects * 27


# ------------------------------------------------------------------ compliance
def test_robots_disallow_blocks_everything(web, seeded):
    w = web({"https://strict.ng/robots.txt": (200, "text/plain", "User-agent: *\nDisallow: /\n")})
    src = Source.objects.create(domain="strict.ng", homepage="https://strict.ng/")
    pipeline.check_source(src)
    src.refresh_from_db()
    assert src.permission_status == Source.Permission.ROBOTS_DISALLOW
    with pytest.raises(fetch.FetchBlocked):
        fetch.fetch(src, "https://strict.ng/jamb-maths-2010")
    assert w.requested == ["https://strict.ng/robots.txt"]  # never fetched anything else


def test_robots_403_means_disallow(web, seeded):
    web({"https://locked.ng/robots.txt": (403, "text/plain", "")})
    src = Source.objects.create(domain="locked.ng", homepage="https://locked.ng/")
    compliance.check_robots(src, fetch.raw_get)
    assert src.permission_status == Source.Permission.ROBOTS_DISALLOW


def test_terms_scan_marks_prohibited_and_never_auto_permits(web, seeded):
    web({
        "https://a.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
        "https://a.ng/": (200, "text/html", '<a href="/terms">Terms of Use</a>'),
        "https://a.ng/terms": (200, "text/html", TERMS_STRICT),
        "https://b.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
        "https://b.ng/": (200, "text/html", '<a href="/terms-of-use">Terms</a>'),
        "https://b.ng/terms-of-use": (200, "text/html", TERMS_LOOSE),
    })
    a = Source.objects.create(domain="a.ng", homepage="https://a.ng/")
    b = Source.objects.create(domain="b.ng", homepage="https://b.ng/")
    pipeline.check_source(a)
    pipeline.check_source(b)
    a.refresh_from_db(); b.refresh_from_db()
    assert a.permission_status == Source.Permission.TERMS_PROHIBIT and a.terms_flags
    assert b.permission_status == Source.Permission.NEEDS_REVIEW  # loose terms still need a human decision
    assert a.crawl_delay_seconds >= 2 and not a.may_extract and not b.may_extract


def test_human_permission_is_never_overwritten_by_checks(web, seeded):
    web({"https://ok.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
         "https://ok.ng/": (200, "text/html", '<a href="/terms">Terms</a>'),
         "https://ok.ng/terms": (200, "text/html", TERMS_STRICT)})
    src = Source.objects.create(domain="ok.ng", homepage="https://ok.ng/", permission_status=Source.Permission.PERMITTED)
    pipeline.check_source(src, force=True)
    src.refresh_from_db()
    assert src.permission_status == Source.Permission.PERMITTED


def test_extraction_fetch_requires_permission(web, seeded):
    web({"https://n.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
         "https://n.ng/jamb-maths-2010": (200, "text/html", "<p>1. What is 2+2?</p>")})
    src = Source.objects.create(domain="n.ng", homepage="https://n.ng/", permission_status=Source.Permission.NEEDS_REVIEW)
    with pytest.raises(fetch.FetchBlocked, match="no permission"):
        fetch.fetch(src, "https://n.ng/jamb-maths-2010", purpose="extraction")
    src.permission_status = Source.Permission.PERMITTED
    src.save()
    assert fetch.fetch(src, "https://n.ng/jamb-maths-2010", purpose="extraction").status == 200


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "rl"}})
def test_per_domain_rate_limit():
    src = Source(domain="slow.ng", crawl_delay_seconds=30)
    fetch._acquire_slot(src, max_wait=0)
    with pytest.raises(fetch.RateLimited):
        fetch._acquire_slot(src, max_wait=0)


# ------------------------------------------------------------------ discovery
def test_crawl_records_relevant_documents_only(web, seeded):
    web({
        "https://pq.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
        "https://pq.ng/": (200, "text/html", """<title>Past questions</title>
            <a href="/jamb">JAMB past questions</a> <a href="/about">About</a> <a href="/admin/x">Admin</a>
            <a href="https://other.ng/jamb-maths-2001.pdf">elsewhere</a>"""),
        "https://pq.ng/jamb": (200, "text/html", """<title>JAMB</title>
            <a href="/files/jamb-mathematics-past-questions-2003.pdf">Maths 2003 PDF</a>
            <a href="/jamb/biology/2010">JAMB Biology 2010 questions</a>
            <a href="/waec-biology-2010">WAEC Biology 2010</a>"""),
        "https://pq.ng/jamb/biology/2010": (200, "text/html", "<title>JAMB Biology 2010 Past Questions</title>"),
    })
    src = pipeline.add_seed("https://pq.ng/")
    pipeline.check_source(src)
    out = pipeline.crawl_source(src)
    urls = set(SourceDocument.objects.values_list("url", flat=True))
    assert "https://pq.ng/files/jamb-mathematics-past-questions-2003.pdf" in urls
    assert "https://pq.ng/jamb/biology/2010" in urls
    assert not any("waec" in u or "other.ng" in u or "/about" in u for u in urls)
    pdf = SourceDocument.objects.get(url__endswith=".pdf")
    assert (pdf.kind, pdf.subject.slug, pdf.year) == ("pdf", "mathematics", 2003)
    assert out["pages_crawled"] >= 2
    assert pipeline.crawl_source(src) == {"skipped": "crawled this week"}  # no repeat processing


class FakeProvider(search.Provider):
    name = "fake"

    def available(self):
        return True

    def search(self, query, n):
        return [search.SearchHit("https://site1.ng/jamb-physics-past-questions-2012.pdf", "JAMB Physics 2012", "", self.name),
                search.SearchHit("https://site2.ng/waec-physics-2012", "WAEC Physics 2012", "", self.name),
                search.SearchHit("https://site3.ng/blog/study-tips", "Study tips", "", self.name)]


def test_discover_target_records_hits_and_updates_matrix(seeded, monkeypatch):
    monkeypatch.setattr(search, "PROVIDERS", [FakeProvider()])
    matrix.ensure_matrix("jamb", 2012, 2012)
    t = ResearchTarget.objects.get(exam_year__year=2012, subject__slug="physics")
    out = pipeline.discover_target(t)
    assert out["providers"] == ["fake"] and out["hits"] > 0
    assert SourceDocument.objects.filter(url__contains="site1.ng").exists()
    assert not SourceDocument.objects.filter(url__contains="site2.ng").exists()
    t.refresh_from_db()
    assert t.status == ResearchTarget.Status.SOURCES_FOUND and t.search_attempts == 1 and t.documents_found == 1
    assert Source.objects.filter(domain="site1.ng", discovered_via="fake").exists()


def test_discover_without_providers_explains(seeded, monkeypatch):
    monkeypatch.setattr(search, "PROVIDERS", [])
    matrix.ensure_matrix("jamb", 2001, 2001)
    t = ResearchTarget.objects.filter(exam_year__year=2001).first()
    assert "No search provider" in pipeline.discover_target(t)["note"]


# ------------------------------------------------------------------ jobs
def test_jobs_are_idempotent_and_resumable():
    with jobs.run("verify", "k1") as j:
        j["result"] = {"ok": 1}
    with jobs.run("verify", "k1") as j:
        assert j is None  # already succeeded
    with pytest.raises(RuntimeError):
        with jobs.run("verify", "k2"):
            raise RuntimeError("boom")
    job = ExtractionJob.objects.get(idempotency_key="k2")
    assert job.status == "failed" and "boom" in job.error
    with jobs.run("verify", "k2") as j:  # failed jobs retry
        assert j is not None
    ExtractionJob.objects.filter(idempotency_key="k3").delete()
    stuck = ExtractionJob.objects.create(kind="verify", idempotency_key="k3", status="running")
    ExtractionJob.objects.filter(pk=stuck.pk).update(started_at="2020-01-01T00:00:00Z")
    assert jobs.resume_stale() == 1
