"""Coverage report. Counts only canonical questions (duplicates excluded), so numbers are never inflated."""
from django.db.models import Count, Q
from django.utils import timezone

from apps.examinations.models import ExamSubject

from .models import ExtractionJob, PastQuestion, ResearchTarget, Source, SourceDocument

V = PastQuestion.Verification


def coverage(exam_code: str = "jamb") -> dict:
    qs = PastQuestion.objects.filter(examination__code=exam_code, duplicate_of__isnull=True)
    live = qs.exclude(verification_status=V.REJECTED)
    targets = ResearchTarget.objects.filter(exam_year__examination__code=exam_code).select_related("exam_year", "subject")
    years = sorted(set(targets.values_list("exam_year__year", flat=True)))
    subjects = list(ExamSubject.objects.filter(examination__code=exam_code).select_related("subject")
                    .order_by("subject__name").values_list("subject_id", "subject__name"))

    per_subject = {r["subject_id"]: r for r in live.values("subject_id").annotate(
        total=Count("id"), verified=Count("id", filter=Q(verification_status=V.VERIFIED)))}
    per_year = {r["year"]: r for r in live.values("year").annotate(
        total=Count("id"), verified=Count("id", filter=Q(verification_status=V.VERIFIED)))}

    grid = {}
    for t in targets:
        grid.setdefault(t.subject_id, {})[t.exam_year.year] = {
            "status": t.status, "questions": t.questions_extracted, "verified": t.questions_verified,
            "documents": t.documents_found, "searches": t.search_attempts}
    missing = [{"subject": t.subject.name, "year": t.exam_year.year, "status": t.status}
               for t in targets.exclude(status__in=[ResearchTarget.Status.EXTRACTED, ResearchTarget.Status.VERIFIED])
               .order_by("subject__name", "exam_year__year")]

    sources = Source.objects.all()
    docs = SourceDocument.objects.all()
    return {
        "generated_at": timezone.now().isoformat(),
        "exam": exam_code,
        "years": years,
        "totals": {
            "questions": live.count(),
            "verified": live.filter(verification_status=V.VERIFIED).count(),
            "awaiting_human_verification": live.filter(verification_status__in=[V.UNVERIFIED, V.AUTO_CHECKED, V.NEEDS_REVIEW]).count(),
            "needs_review": live.filter(verification_status=V.NEEDS_REVIEW).count(),
            "rejected": qs.filter(verification_status=V.REJECTED).count(),
            "duplicates_found": PastQuestion.objects.filter(examination__code=exam_code, duplicate_of__isnull=False).count(),
            "awaiting_copyright_clearance": live.exclude(rights_status=PastQuestion.Rights.CLEARED).count(),
            "sources_awaiting_permission_review": sources.filter(permission_status__in=[Source.Permission.UNKNOWN, Source.Permission.NEEDS_REVIEW]).count(),
            "subjects_covered": live.exclude(subject__isnull=True).values("subject").distinct().count(),
            "subjects_total": len(subjects),
            "years_covered": live.exclude(year__isnull=True).values("year").distinct().count(),
            "years_total": len(years),
            "cells_total": targets.count(),
            "cells_with_questions": targets.filter(status__in=[ResearchTarget.Status.EXTRACTED, ResearchTarget.Status.VERIFIED]).count(),
            "cells_missing": len(missing),
            "sources_discovered": sources.count(),
            "sources_processed": sources.filter(documents__status=SourceDocument.Status.EXTRACTED).distinct().count(),
            "documents_discovered": docs.count(),
            "documents_extracted": docs.filter(status=SourceDocument.Status.EXTRACTED).count(),
            "documents_blocked": docs.filter(status=SourceDocument.Status.BLOCKED).count(),
            "failed_jobs": ExtractionJob.objects.filter(status=ExtractionJob.Status.FAILED).count(),
        },
        "per_subject": [{"subject_id": sid, "subject": name, "questions": per_subject.get(sid, {}).get("total", 0),
                         "verified": per_subject.get(sid, {}).get("verified", 0)} for sid, name in subjects],
        "per_year": [{"year": y, "questions": per_year.get(y, {}).get("total", 0), "verified": per_year.get(y, {}).get("verified", 0)}
                     for y in years],
        "matrix": [{"subject_id": sid, "subject": name, "cells": [{"year": y, **grid.get(sid, {}).get(y, {"status": "missing"})} for y in years]}
                   for sid, name in subjects],
        "missing": missing,
        "sources_by_permission": dict(sources.values_list("permission_status").annotate(n=Count("id")).order_by()),
        "target_status": dict(targets.values_list("status").annotate(n=Count("id")).order_by()),
    }
