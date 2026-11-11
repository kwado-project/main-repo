"""Move a research question into Kwado's question bank — only when verified AND rights-cleared.

It lands as a DRAFT in the normal Import → Validate → Verify answer → Review → Publish workflow,
with the agreed answer recorded as a suggestion, so a content reviewer still verifies the key.
"""
from django.db import transaction

from apps.questions.models import Question, QuestionOption

from .extraction.structure import to_record
from .models import PastQuestion


class NotEligible(Exception):
    pass


@transaction.atomic
def promote(q: PastQuestion, user) -> Question:
    if q.promoted_question_id:
        return q.promoted_question
    if q.verification_status != PastQuestion.Verification.VERIFIED:
        raise NotEligible("Only human-verified questions can be promoted.")
    if q.rights_status != PastQuestion.Rights.CLEARED or not q.source.may_extract:
        raise NotEligible("Copyright is not cleared for this question's source.")
    if q.duplicate_of_id:
        raise NotEligible(f"This is a duplicate of research question {q.duplicate_of_id}; promote that one.")
    if not q.subject_id:
        raise NotEligible("Set the subject first.")
    rec = to_record(q)
    passage_note = f"\n\nPassage:\n{q.passage}" if q.passage else ""
    bank = Question.objects.create(
        examination=q.examination, subject=q.subject, topic=q.topic, text=q.text + passage_note,
        explanation=rec["explanation"] or "", difficulty=q.difficulty or 2, exam_year=q.year,
        source=f"{q.source.domain} ({q.source_url})"[:200], is_official_past_question=True, created_by=user,
        status=Question.Status.DRAFT,
        review_notes=(f"Imported from research question {q.pk}. Suggested answer: {rec['correct_answer']} "
                      f"(human-verified in research; verify again here before publishing)."),
    )
    QuestionOption.objects.bulk_create([QuestionOption(question=bank, label=o.label, text=o.text, order=i)
                                        for i, o in enumerate(q.options.all())])
    PastQuestion.objects.filter(pk=q.pk).update(promoted_question=bank)
    return bank
