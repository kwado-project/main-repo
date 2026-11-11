"""The research matrix: one ResearchTarget per examination × subject × year."""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.examinations.models import Examination, ExamSubject

from .models import ExaminationYear, PastQuestion, ResearchTarget, SourceDocument

T = ResearchTarget.Status


def get_exam(code: str = "jamb") -> Examination:
    exam = Examination.objects.filter(code=code).first()
    if not exam:
        raise ValueError(f"No examination with code '{code}'. Create it in the admin first.")
    return exam


@transaction.atomic
def ensure_matrix(exam_code: str = "jamb", year_from: int | None = None, year_to: int | None = None) -> dict:
    """Create missing year and target rows. Safe to run repeatedly."""
    exam = get_exam(exam_code)
    year_from = year_from or settings.RESEARCH_YEAR_FROM
    year_to = year_to or settings.RESEARCH_YEAR_TO
    subject_ids = list(ExamSubject.objects.filter(examination=exam).values_list("subject_id", flat=True))
    if not subject_ids:
        raise ValueError(f"{exam.name} has no subjects linked. Add them under Exam rules first.")
    created_years = created_targets = 0
    for year in range(year_from, year_to + 1):
        ey, made = ExaminationYear.objects.get_or_create(examination=exam, year=year)
        created_years += made
        existing = set(ResearchTarget.objects.filter(exam_year=ey).values_list("subject_id", flat=True))
        new = [ResearchTarget(exam_year=ey, subject_id=s) for s in subject_ids if s not in existing]
        ResearchTarget.objects.bulk_create(new)
        created_targets += len(new)
    total = ResearchTarget.objects.filter(exam_year__examination=exam).count()
    return {"exam": exam.name, "years": f"{year_from}-{year_to}", "subjects": len(subject_ids),
            "created_years": created_years, "created_targets": created_targets, "total_targets": total}


def refresh_target(target: ResearchTarget) -> ResearchTarget:
    """Recompute counts and status from the data. Never downgrades UNAVAILABLE unless data appears."""
    exam = target.exam_year.examination
    year = target.exam_year.year
    docs = SourceDocument.objects.filter(subject=target.subject_id, year=year).exclude(examination_guess__in=["waec", "neco", "gce", "nabteb", "post-utme"])
    qs = PastQuestion.objects.filter(examination=exam, subject=target.subject_id, year=year, duplicate_of__isnull=True)
    target.documents_found = docs.count()
    target.questions_extracted = qs.count()
    target.questions_verified = qs.filter(verification_status=PastQuestion.Verification.VERIFIED).count()
    if target.questions_verified:
        target.status = T.VERIFIED
    elif target.questions_extracted:
        target.status = T.EXTRACTED
    elif target.documents_found:
        target.status = T.SOURCES_FOUND
    elif target.search_attempts >= settings.RESEARCH_MAX_SEARCH_ATTEMPTS:
        target.status = T.UNAVAILABLE
    elif target.status != T.SEARCHING:
        target.status = T.MISSING
    target.save(update_fields=["documents_found", "questions_extracted", "questions_verified", "status", "updated_at"])
    return target


def refresh_all(exam_code: str = "jamb"):
    for t in ResearchTarget.objects.filter(exam_year__examination__code=exam_code).select_related("exam_year__examination"):
        refresh_target(t)


def targets_needing_search(exam_code: str = "jamb", limit: int = 20):
    """Gaps first, least-searched first; skip recently searched and exhausted cells."""
    cutoff = timezone.now() - timedelta(days=settings.RESEARCH_SEARCH_AGAIN_AFTER_DAYS)
    return (ResearchTarget.objects
            .filter(exam_year__examination__code=exam_code, status__in=[T.MISSING, T.SOURCES_FOUND],
                    search_attempts__lt=settings.RESEARCH_MAX_SEARCH_ATTEMPTS)
            .filter(Q(last_searched_at__isnull=True) | Q(last_searched_at__lt=cutoff))
            .select_related("exam_year__examination", "subject")
            .order_by("search_attempts", "status", "-exam_year__year")[:limit])


def gaps(exam_code: str = "jamb"):
    return (ResearchTarget.objects.filter(exam_year__examination__code=exam_code)
            .exclude(status__in=[T.EXTRACTED, T.VERIFIED])
            .select_related("exam_year", "subject").order_by("subject__name", "exam_year__year"))


def status_counts(exam_code: str = "jamb") -> dict:
    return dict(ResearchTarget.objects.filter(exam_year__examination__code=exam_code)
                .values_list("status").annotate(n=Count("id")).order_by())
