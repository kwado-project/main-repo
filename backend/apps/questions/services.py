"""Question-bank workflow: Import → Validate → Verify answer → Review → Publish."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import audit

from .models import AnswerKey, Question, QuestionOption

S = Question.Status


def validate_question(q: Question) -> list[str]:
    problems = []
    opts = list(q.options.all())
    if len(q.text.strip()) < 5:
        problems.append("Question text is too short.")
    if len(opts) < 2:
        problems.append("A question needs at least two options.")
    if len({o.text.strip().lower() for o in opts}) != len(opts):
        problems.append("Options must be distinct.")
    if not q.topic_id:
        problems.append("Assign a topic.")
    if q.topic_id and q.topic.subject_id != q.subject_id:
        problems.append("Topic does not belong to the subject.")
    if not q.explanation.strip():
        problems.append("Add an explanation students will see after answering.")
    return problems


@transaction.atomic
def transition(q: Question, target: str, actor, *, correct_option_id=None, notes="", source=""):
    q = Question.objects.select_for_update().get(pk=q.pk)
    if target == S.VALIDATED:
        problems = validate_question(q)
        if problems:
            raise ValidationError({"detail": problems})
        if q.status not in (S.DRAFT, S.REJECTED):
            raise ValidationError({"detail": "Only drafts can be validated."})
    elif target == S.ANSWER_VERIFIED:
        if q.status not in (S.VALIDATED, S.ANSWER_VERIFIED):
            raise ValidationError({"detail": "Validate the question before verifying its answer."})
        opt = QuestionOption.objects.filter(pk=correct_option_id, question=q).first()
        if not opt:
            raise ValidationError({"correct_option": "Choose the correct option."})
        # A human always verifies the key — including for AI-generated questions.
        AnswerKey.objects.update_or_create(question=q, defaults={
            "correct_option": opt, "verified_by": actor, "verified_at": timezone.now(),
            "verification_source": source[:200]})
    elif target == S.IN_REVIEW:
        if q.status != S.ANSWER_VERIFIED:
            raise ValidationError({"detail": "Verify the answer before sending for review."})
    elif target == S.PUBLISHED:
        if q.status != S.IN_REVIEW:
            raise ValidationError({"detail": "Only reviewed questions can be published."})
        key = getattr(q, "answer_key", None)
        if not key or not key.is_verified:
            raise ValidationError({"detail": "A verified answer key is required to publish."})
        if key.verified_by_id == actor.id and actor.role != "admin":
            raise ValidationError({"detail": "A second reviewer must publish a question you verified."})
        q.published_at = timezone.now()
        q.reviewed_by = actor
    elif target == S.REJECTED:
        q.review_notes = notes[:2000]
    elif target == S.DRAFT:
        pass
    else:
        raise ValidationError({"detail": "Unknown status."})
    q.status = target
    q.save()
    audit(f"question.{target}", actor=actor, target=q)
    from django.core.cache import cache
    cache.delete_many([f"qpool:{q.subject_id}:{t}:{e}" for t in (None, q.topic_id) for e in (None, q.examination_id)])
    return q


def import_rows(rows: list[dict], actor) -> dict:
    """Import JSON rows. Each row: subject_id, topic_id?, text, options[{label,text}], explanation?,
    difficulty?, exam_year?, source?, examination_id?, answer? (label, recorded as a *suggestion* only)."""
    created, errors = 0, []
    for i, r in enumerate(rows):
        try:
            with transaction.atomic():
                q = Question.objects.create(
                    subject_id=r["subject_id"], topic_id=r.get("topic_id"), examination_id=r.get("examination_id"),
                    text=r["text"], explanation=r.get("explanation", ""), difficulty=int(r.get("difficulty", 2)),
                    exam_year=r.get("exam_year"), source=r.get("source", "")[:200],
                    is_official_past_question=bool(r.get("is_official_past_question")),
                    solution_steps=r.get("solution_steps", []), created_by=actor, status=S.DRAFT,
                    review_notes=f"Suggested answer from import: {r['answer']}" if r.get("answer") else "",
                )
                for j, o in enumerate(r["options"]):
                    QuestionOption.objects.create(question=q, label=o["label"][:2], text=o["text"], order=j)
                created += 1
        except Exception as e:  # noqa: BLE001
            errors.append({"row": i, "error": str(e)[:200]})
    return {"created": created, "errors": errors}
