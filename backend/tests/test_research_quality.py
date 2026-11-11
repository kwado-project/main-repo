"""Stage 3: quality control. Invented sample questions only."""
import pytest
from django.test import override_settings

from apps.examinations.models import Examination, Subject
from apps.research import pipeline, review
from apps.research.extraction.structure import question_hash, to_record
from apps.research.models import (PastAnswer, PastQuestion, PastQuestionOption, Source, SourceDocument,
                                  VerificationRecord)

pytestmark = pytest.mark.django_db
V = PastQuestion.Verification


def make_q(text, options, answer=None, *, domain="lic.ng", number=1, year=2010, subject="mathematics", flags=None,
           has_diagram=False, url=None):
    src, _ = Source.objects.get_or_create(domain=domain, defaults={"permission_status": Source.Permission.PERMITTED})
    doc = SourceDocument.objects.create(source=src, url=url or f"https://{domain}/doc-{SourceDocument.objects.count()}")
    q = PastQuestion.objects.create(
        examination=Examination.objects.get(code="jamb"), subject=Subject.objects.get(slug=subject), year=year,
        question_number=number, text=text, normalized_hash=question_hash(text, options), source=src, document=doc,
        source_url=doc.url, extraction_method="html", extraction_confidence=0.9, flags=flags or [],
        has_diagram=has_diagram, rights_status="cleared")
    PastQuestionOption.objects.bulk_create([PastQuestionOption(question=q, label=k, text=v) for k, v in options.items()])
    if answer:
        PastAnswer.objects.create(question=q, label=answer, origin="source")
    return PastQuestion.objects.get(pk=q.pk)


OPTS = {"A": "Lagos", "B": "Abuja", "C": "Kano", "D": "Ibadan"}


def issues(out):
    return " ".join(out.get("issues", []))


def test_clean_question_is_auto_checked(seeded):
    out = pipeline.verify_question(make_q("What is the capital of Nigeria?", OPTS, "B"))
    assert out["status"] == V.AUTO_CHECKED and out["confidence"] >= 0.85
    assert pipeline.verify_question(PastQuestion.objects.get()) == {"skipped": "already verified with these checks"}


@pytest.mark.parametrize("text,opts,ans,expect", [
    ("Capital?", OPTS, "B", "completeness"),
    ("What is the capital of Nigeria?", {"A": "Lagos", "B": "Abuja", "C": "Kano"}, "B", "only 3 options"),
    ("What is the capital of Nigeria?", OPTS, "E", "answer E is not an option"),
    ("What is the capital of Nigeria?", OPTS, None, "source gives no answer"),
    ("What is the capital of Nigeria?", {"A": "Lagos", "B": "Abuja", "C": "lagos", "D": "Kano"}, "B", "duplicate option"),
])
def test_problem_questions_need_review(seeded, text, opts, ans, expect):
    out = pipeline.verify_question(make_q(text, opts, ans))
    assert out["status"] == V.NEEDS_REVIEW and expect in issues(out)


def test_wrong_exam_and_missing_diagram_are_flagged(seeded):
    q = make_q("Use the diagram below to find the angle.", {"A": "30", "B": "45", "C": "60", "D": "90"}, "B",
               flags=["document header mentions WAEC, not JAMB"], has_diagram=True)
    out = pipeline.verify_question(q)
    assert "exam_attribution" in issues(out) and "diagram" in issues(out)


def test_arithmetic_recheck_flags_wrong_key_without_changing_it(seeded):
    q = make_q("Evaluate 3 + 4 × 2", {"A": "14", "B": "11", "C": "9", "D": "10"}, "A")
    out = pipeline.verify_question(q)
    assert "source answer disagrees with arithmetic" in issues(out)
    assert q.answers.get().label == "A"  # original key untouched
    ok = make_q("Evaluate 2^3 + 1", {"A": "7", "B": "9", "C": "8", "D": "10"}, "B", number=2)
    assert pipeline.verify_question(ok)["status"] == V.AUTO_CHECKED


def test_cross_source_agreement_and_conflict(seeded):
    a = make_q("Which gas do plants absorb for photosynthesis?", {"A": "Oxygen", "B": "Carbon dioxide", "C": "Nitrogen", "D": "Helium"}, "B",
               domain="one.ng", subject="biology")
    pipeline.verify_question(a)
    # Same question on another site, options re-ordered — letters differ but the answer TEXT agrees.
    b = make_q("Which gas do plants absorb for photosynthesis ?", {"A": "Carbon dioxide", "B": "Oxygen", "C": "Helium", "D": "Nitrogen"}, "A",
               domain="two.ng", subject="biology")
    out = pipeline.verify_question(b)
    b.refresh_from_db()
    assert b.duplicate_of_id == a.pk and out["status"] == V.AUTO_CHECKED
    assert VerificationRecord.objects.filter(question=b, check_name="cross_source", result="pass").exists()
    # A third site claiming a different answer → conflict, human review needed.
    c = make_q("Which gas do plants absorb for photosynthesis?", {"A": "Oxygen", "B": "Carbon dioxide", "C": "Nitrogen", "D": "Helium"}, "A",
               domain="three.ng", subject="biology")
    out = pipeline.verify_question(c)
    assert out["status"] == V.NEEDS_REVIEW and "independent sources give different answers" in issues(out)


def test_near_duplicate_with_small_wording_change(seeded):
    a = make_q("Find the value of x if 2x + 3 = 11", {"A": "3", "B": "4", "C": "5", "D": "7"}, "B", domain="one.ng")
    pipeline.verify_question(a)
    b = make_q("Find the value of x, if 2x + 3 = 11.", {"A": "3", "B": "4", "C": "5", "D": "7"}, "B", domain="two.ng")
    pipeline.verify_question(b)
    b.refresh_from_db()
    assert b.duplicate_of_id == a.pk


def test_human_decision_is_never_overridden(seeded, make_student):
    q = make_q("What is the capital of Nigeria?", OPTS, None)
    reviewer = make_student("rev@example.com")
    with pytest.raises(ValueError, match="Confirm the correct answer"):
        review.mark_verified(q, reviewer)
    with pytest.raises(ValueError, match="not one of"):
        review.mark_verified(q, reviewer, "E")
    review.mark_verified(q, reviewer, "B", "checked against syllabus")
    assert pipeline.verify_question(q, force=True)["status"] == V.VERIFIED
    assert to_record(PastQuestion.objects.get(pk=q.pk))["correct_answer"] == "B"
    review.mark_rejected(q, reviewer, "garbled scan")
    q.refresh_from_db()
    assert q.verification_status == V.REJECTED and q.text == "What is the capital of Nigeria?"


@override_settings(RESEARCH_AI_REVIEW=True)
def test_ai_review_is_advisory_only(seeded, monkeypatch):
    from apps.research.quality import ai_review
    monkeypatch.setattr(ai_review, "review", lambda q: {"answer": "C", "confidence": 0.9, "issues": [], "model": "m", "is_mock": False})
    q = make_q("What is the capital of Nigeria?", OPTS, "B")
    out = pipeline.verify_question(q)
    assert out["status"] == V.NEEDS_REVIEW and "AI disagrees" in issues(out)
    assert set(q.answers.values_list("origin", "label")) == {("source", "B"), ("ai", "C")}
    assert to_record(PastQuestion.objects.get(pk=q.pk))["correct_answer"] == "B"  # AI never becomes the answer
