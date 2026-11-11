"""Human decisions. Recorded as new rows; the extracted question itself is never edited."""
from django.db import transaction

from .models import PastAnswer, PastQuestion, VerificationRecord

V = PastQuestion.Verification


@transaction.atomic
def mark_verified(q: PastQuestion, user, answer_label: str | None = None, note: str = "") -> PastQuestion:
    labels = set(q.options.values_list("label", flat=True))
    if answer_label:
        answer_label = answer_label.strip().upper()
        if answer_label not in labels:
            raise ValueError(f"{answer_label} is not one of this question's options")
        PastAnswer.objects.create(question=q, label=answer_label, origin=PastAnswer.Origin.HUMAN, recorded_by=user,
                                  note=note[:255])
    elif not q.answers.filter(origin__in=[PastAnswer.Origin.SOURCE, PastAnswer.Origin.HUMAN]).exists():
        raise ValueError("Confirm the correct answer: the source does not provide one.")
    VerificationRecord.objects.create(question=q, check_name="human_review", result=VerificationRecord.Result.PASS,
                                      actor=VerificationRecord.Actor.HUMAN, user=user,
                                      details={"answer": answer_label, "note": note[:500]})
    PastQuestion.objects.filter(pk=q.pk).update(verification_status=V.VERIFIED)
    q.refresh_from_db()
    return q


@transaction.atomic
def mark_rejected(q: PastQuestion, user, reason: str) -> PastQuestion:
    if not reason.strip():
        raise ValueError("Give a reason for rejecting.")
    VerificationRecord.objects.create(question=q, check_name="human_review", result=VerificationRecord.Result.FAIL,
                                      actor=VerificationRecord.Actor.HUMAN, user=user, details={"reason": reason[:500]})
    PastQuestion.objects.filter(pk=q.pk).update(verification_status=V.REJECTED)
    q.refresh_from_db()
    return q
