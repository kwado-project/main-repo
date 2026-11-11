"""Stage 4: autonomous cycle, coverage report, admin API, promotion and CLI. Fake web, invented questions."""
import json

import pytest
from django.core.management import call_command

from apps.questions.models import Question
from apps.research import pipeline, reports
from apps.research.discovery import search
from apps.research.models import PastQuestion, ResearchTarget, Source, SourceDocument

from test_research_discovery import ROBOTS_OK, TERMS_STRICT, web  # noqa: F401  (shared fixture)
from test_research_extraction import PDF_LINES, _pdf

pytestmark = pytest.mark.django_db

HTML_PAGE = """<html><head><title>JAMB Biology 2004 Past Questions</title></head><body><article>
<p>1. Which organelle releases energy?</p><p>A. Nucleus</p><p>B. Mitochondrion</p><p>C. Ribosome</p><p>D. Vacuole</p><p>Answer: B</p>
<p>2. Blood is pumped by the</p><p>A. lungs B. heart C. liver D. kidney</p><p>Answer: B</p>
<p>Filler text describing these past questions in enough detail to be treated as the main article of the page.</p>
</article></body></html>"""


class Provider(search.Provider):
    name = "fake"

    def available(self):
        return True

    def search(self, query, n):
        if "Biology" not in query or "2004" not in query:
            return []
        return [search.SearchHit("https://good.ng/jamb-biology-past-questions-2004.pdf", "JAMB Biology 2004", "", self.name),
                search.SearchHit("https://good.ng/jamb/biology/2004", "JAMB Biology 2004 Past Questions", "", self.name),
                search.SearchHit("https://strict.ng/jamb-biology-2004", "JAMB Biology 2004 questions", "", self.name),
                search.SearchHit("https://maybe.ng/jamb-biology-2004.pdf", "JAMB Biology 2004 PDF", "", self.name)]


@pytest.fixture
def internet(web, monkeypatch):  # noqa: F811
    monkeypatch.setattr(search, "PROVIDERS", [Provider()])
    return web({
        "https://good.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
        "https://good.ng/": (200, "text/html", '<a href="/terms">Terms</a>'),
        "https://good.ng/terms": (200, "text/html", "<p>Free to use for education.</p>"),
        "https://good.ng/jamb-biology-past-questions-2004.pdf": (200, "application/pdf", _pdf(PDF_LINES)),
        "https://good.ng/jamb/biology/2004": (200, "text/html", HTML_PAGE),
        "https://strict.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
        "https://strict.ng/": (200, "text/html", '<a href="/terms-and-conditions">Terms</a>'),
        "https://strict.ng/terms-and-conditions": (200, "text/html", TERMS_STRICT),
        "https://maybe.ng/robots.txt": (200, "text/plain", ROBOTS_OK),
        "https://maybe.ng/": (200, "text/html", "<p>Hello</p>"),
    })


def admin_client(make_student, auth, email="boss@example.com"):
    u = make_student(email)
    u.role = "admin"
    u.save()
    return u, auth(u)


def test_full_cycle_respects_permissions_and_reports_honestly(seeded, internet, make_student, auth):
    out = pipeline.run_cycle("jamb", targets=500)
    assert not out["errors"], out["errors"]
    assert out["discovery"]["documents_recorded"] >= 3
    # Nobody has granted permission yet: nothing is extracted from anyone.
    assert not PastQuestion.objects.exists()
    perms = dict(Source.objects.values_list("domain", "permission_status"))
    assert perms == {"good.ng": "needs_review", "strict.ng": "terms_prohibit", "maybe.ng": "needs_review"}

    # An admin records permission for good.ng only (with evidence).
    _, api = admin_client(make_student, auth)
    good = Source.objects.get(domain="good.ng")
    r = api.post(f"/api/admin-api/research/sources/{good.id}/permission/", {"status": "permitted"}, format="json")
    assert r.status_code == 400 and "evidence" in r.data
    r = api.post(f"/api/admin-api/research/sources/{good.id}/permission/",
                 {"status": "permitted", "evidence": "Email from good.ng owner, 2026-11-01", "scope": "all JAMB content"}, format="json")
    assert r.status_code == 200 and r.data["permission_status"] == "permitted"

    out2 = pipeline.run_cycle("jamb", targets=0)
    assert not out2["errors"], out2["errors"]
    assert out2["extraction"]["documents"] == 2
    # PDF: organelle + photosynthesis; web page: organelle + heart → 3 distinct questions, 1 duplicate.
    canonical = PastQuestion.objects.filter(duplicate_of__isnull=True)
    assert canonical.count() == 3 and PastQuestion.objects.filter(duplicate_of__isnull=False).count() == 1
    assert set(PastQuestion.objects.values_list("source__domain", flat=True)) == {"good.ng"}
    assert set(PastQuestion.objects.values_list("rights_status", flat=True)) == {"cleared"}
    assert not SourceDocument.objects.filter(source__domain="strict.ng").exclude(status="discovered").exclude(status="blocked").exists()

    rep = reports.coverage("jamb")
    t = rep["totals"]
    assert (t["questions"], t["verified"], t["subjects_covered"], t["years_covered"]) == (3, 0, 1, 1)
    assert t["awaiting_human_verification"] == 3 and t["sources_processed"] == 1 and t["duplicates_found"] == 1
    assert t["cells_with_questions"] == 1 and t["cells_missing"] == t["cells_total"] - 1
    cell = ResearchTarget.objects.get(subject__slug="biology", exam_year__year=2004)
    assert cell.status == "extracted" and cell.questions_extracted == 3
    bio = next(r for r in rep["matrix"] if r["subject"] == "Biology")
    assert next(c for c in bio["cells"] if c["year"] == 2004)["questions"] == 3

    # Re-running changes nothing (no repeated processing).
    pipeline.run_cycle("jamb", targets=0)
    assert PastQuestion.objects.count() == 4


def test_review_promote_and_export_via_api(seeded, internet, make_student, auth):
    pipeline.run_cycle("jamb", targets=500)
    u, api = admin_client(make_student, auth)
    good = Source.objects.get(domain="good.ng")
    api.post(f"/api/admin-api/research/sources/{good.id}/permission/", {"status": "permitted", "evidence": "signed letter"}, format="json")
    pipeline.run_cycle("jamb", targets=0)

    lst = api.get("/api/admin-api/research/questions/?subject=" + str(PastQuestion.objects.first().subject_id)).data
    assert lst["count"] == 3
    qid = lst["results"][0]["id"]
    detail = api.get(f"/api/admin-api/research/questions/{qid}/").data
    assert detail["verifications"] and detail["duplicates"]
    assert api.post(f"/api/admin-api/research/questions/{qid}/promote/").status_code == 400  # not verified yet
    assert api.post(f"/api/admin-api/research/questions/{qid}/verify/", {"note": "checked"}, format="json").status_code == 200
    r = api.post(f"/api/admin-api/research/questions/{qid}/promote/")
    assert r.status_code == 200
    bank = Question.objects.get(pk=r.data["question_bank_id"])
    assert bank.status == "draft" and bank.is_official_past_question and bank.exam_year == 2004
    assert "Suggested answer: B" in bank.review_notes and not hasattr(bank, "answer_key")
    api.post(f"/api/admin-api/research/questions/{qid}/classify/", {"difficulty": 1}, format="json")
    assert api.get("/api/admin-api/research/questions/?difficulty=1").data["count"] == 1

    exported = json.loads(api.get("/api/admin-api/research/questions/export/").content)
    assert len(exported) == 3 and {"exam", "year", "subject", "question_number", "question", "options", "correct_answer",
                                   "explanation", "topic", "source_url", "verification_status", "rights_status"} <= set(exported[0])
    ov = api.get("/api/admin-api/research/overview/").data
    assert ov["totals"]["verified"] == 1


def test_permissions_on_research_api(seeded, make_student, auth):
    student = make_student("kid@example.com")
    assert auth(student).get("/api/admin-api/research/overview/").status_code == 403
    cm = make_student("cm@example.com")
    cm.role = "content_manager"
    cm.save()
    api = auth(cm)
    assert api.get("/api/admin-api/research/overview/").status_code == 200
    src = Source.objects.create(domain="x.ng")
    assert api.post(f"/api/admin-api/research/sources/{src.id}/permission/", {"status": "permitted", "evidence": "x"}, format="json").status_code == 403
    assert api.post("/api/admin-api/research/run/", {"action": "cycle"}, format="json").status_code == 403


def test_denying_permission_marks_existing_questions_denied(seeded, internet, make_student, auth):
    pipeline.run_cycle("jamb", targets=500)
    _, api = admin_client(make_student, auth)
    good = Source.objects.get(domain="good.ng")
    api.post(f"/api/admin-api/research/sources/{good.id}/permission/", {"status": "permitted", "evidence": "letter"}, format="json")
    pipeline.run_cycle("jamb", targets=0)
    api.post(f"/api/admin-api/research/sources/{good.id}/permission/", {"status": "denied"}, format="json")
    assert set(PastQuestion.objects.values_list("rights_status", flat=True)) == {"denied"}
    assert reports.coverage()["totals"]["awaiting_copyright_clearance"] == 3


def test_cli_matrix_report_and_export(seeded, internet, tmp_path, capsys):
    call_command("research", "matrix")
    call_command("research", "report")
    assert "Coverage" in capsys.readouterr().out
    out = tmp_path / "x.json"
    call_command("research", "export", "--out", str(out))
    assert json.loads(out.read_text()) == []


@pytest.mark.parametrize("what", ["cycle", "verify", "matrix"])
def test_run_button_succeeds_and_is_audited(seeded, make_student, auth, what, monkeypatch):
    from apps.core.models import AuditLog
    from apps.research import tasks

    queued = []
    monkeypatch.setattr(tasks.research_cycle, "delay", lambda *a, **k: queued.append("cycle") or type("R", (), {"id": "t1"})())
    monkeypatch.setattr(tasks.verify_pending_task, "delay", lambda *a, **k: queued.append("verify") or type("R", (), {"id": "t2"})())
    _, api = admin_client(make_student, auth)
    r = api.post("/api/admin-api/research/run/", {"action": what}, format="json")
    assert r.status_code in (200, 202), r.content
    if what != "matrix":
        assert queued == [what] and AuditLog.objects.filter(action="research.run", metadata__run=what).exists()
    assert api.post("/api/admin-api/research/run/", {"action": "nope"}, format="json").status_code == 400


def test_other_research_admin_endpoints_succeed(seeded, internet, make_student, auth):
    pipeline.run_cycle("jamb", targets=500)
    _, api = admin_client(make_student, auth)
    src = Source.objects.get(domain="good.ng")
    for path, method, body in [
        ("/api/admin-api/research/overview/", "get", None),
        ("/api/admin-api/research/jobs/?status=failed", "get", None),
        ("/api/admin-api/research/sources/", "get", None),
        (f"/api/admin-api/research/sources/{src.id}/", "get", None),
        (f"/api/admin-api/research/sources/{src.id}/check/", "post", {}),
        (f"/api/admin-api/research/sources/{src.id}/active/", "post", {"is_active": True}),
        ("/api/admin-api/research/documents/", "get", None),
        ("/api/admin-api/research/questions/?awaiting=1", "get", None),
        ("/api/admin-api/research/seeds/", "post", {"url": "https://new.ng/", "name": "New"}),
    ]:
        r = getattr(api, method)(path, body, format="json") if body is not None else api.get(path)
        assert r.status_code < 300, (path, r.status_code, getattr(r, "data", None))
