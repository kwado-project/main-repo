"""Persist parsed questions with full provenance, and export them in the agreed JSON shape."""
import hashlib
import re
import unicodedata

from django.db import transaction

from apps.examinations.models import Examination

from ..discovery.classify import detect_exam, detect_subject, detect_year
from ..discovery.crawler import subject_for
from ..models import PastAnswer, PastExplanation, PastQuestion, PastQuestionOption, SourceDocument

BASE_CONFIDENCE = {"html": 0.9, "pdf_text": 0.85, "ocr": 0.6, "manual": 1.0}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = re.sub(r"[^\w\s²³√π^/=+\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def question_hash(stem: str, options: dict) -> str:
    """Stable fingerprint: normalised stem + option texts in sorted order (order-insensitive)."""
    key = normalize(stem) + "||" + "|".join(sorted(normalize(v) for v in options.values()))
    return hashlib.sha256(key.encode()).hexdigest()


def initial_confidence(method: str, q) -> float:
    c = BASE_CONFIDENCE.get(method, 0.7)
    c -= 0.15 * len(q.warnings)
    if len(q.text) < 12:
        c -= 0.2
    return round(max(0.05, min(1.0, c)), 2)


@transaction.atomic
def save_parsed(doc: SourceDocument, paper, method: str, header_text: str = "") -> dict:
    """Create PastQuestion rows for a parsed document. Re-running is a no-op (unique constraint)."""
    exam = Examination.objects.get(code="jamb")
    header = f"{doc.title} {header_text} {paper.header}".lower()
    subject = doc.subject or subject_for(detect_subject(header))
    year = doc.year or detect_year(header, 1978, 2100)
    exam_in_doc = detect_exam(header)
    created = skipped = 0
    for q in paper.questions:
        if not q.text and not q.options:
            continue
        h = question_hash(q.text, q.options)
        flags = list(q.warnings)
        if exam_in_doc and exam_in_doc != "jamb":
            flags.append(f"document header mentions {exam_in_doc.upper()}, not JAMB")
        pq, made = PastQuestion.objects.get_or_create(
            document=doc, question_number=q.number, normalized_hash=h,
            defaults=dict(
                examination=exam, subject=subject, year=year, text=q.text, passage=q.passage,
                has_math=q.has_math, has_diagram=q.has_diagram, image_refs=q.image_refs,
                source=doc.source, source_url=doc.url, page_number=q.page, extraction_method=method,
                extraction_confidence=initial_confidence(method, q), flags=flags,
                rights_status=PastQuestion.Rights.CLEARED if doc.source.may_extract else PastQuestion.Rights.PERMISSION_PENDING,
            ))
        if not made:
            skipped += 1
            continue
        created += 1
        PastQuestionOption.objects.bulk_create(
            [PastQuestionOption(question=pq, label=lab, text=txt) for lab, txt in sorted(q.options.items())])
        if q.answer:
            PastAnswer.objects.create(question=pq, label=q.answer, origin=PastAnswer.Origin.SOURCE,
                                      note="inline answer" if q.number not in paper.answer_key else "answer key")
        if q.explanation:
            PastExplanation.objects.create(question=pq, text=q.explanation)
    return {"created": created, "already_saved": skipped, "subject": getattr(subject, "name", None), "year": year,
            "warnings": paper.warnings}


def to_record(q: PastQuestion) -> dict:
    """The agreed export shape. Answers/explanations only from the source or a human — never AI."""
    answers = [a for a in q.answers.all() if a.origin != PastAnswer.Origin.AI]
    human = next((a for a in answers if a.origin == PastAnswer.Origin.HUMAN), None)
    chosen = human or (answers[0] if answers else None)
    expl = next((e.text for e in q.explanations.all() if e.origin != PastAnswer.Origin.AI), None)
    return {
        "exam": q.examination.name.split()[0].upper() if q.examination_id else "JAMB",
        "year": q.year,
        "subject": q.subject.name if q.subject_id else None,
        "question_number": q.question_number,
        "question": q.text,
        "passage": q.passage or None,
        "options": {o.label: o.text for o in q.options.all()},
        "correct_answer": chosen.label if chosen else None,
        "explanation": expl,
        "topic": q.topic.name if q.topic_id else None,
        "source_url": q.source_url,
        "page_number": q.page_number,
        "extraction_method": q.extraction_method,
        "extraction_confidence": q.extraction_confidence,
        "verification_status": q.verification_status,
        "rights_status": q.rights_status,
        "flags": q.flags,
    }
