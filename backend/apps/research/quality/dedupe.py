"""Duplicate detection and cross-source answer comparison."""
from django.db.models import Q
from rapidfuzz import fuzz

from ..extraction.structure import normalize
from ..models import PastQuestion

NEAR_DUPLICATE_SCORE = 92


def _fingerprint(q) -> str:
    return normalize(q.text) + " || " + " | ".join(sorted(normalize(o.text) for o in q.options.all()))


def find_duplicate(q: PastQuestion) -> PastQuestion | None:
    """Earliest canonical question that is the same as `q` (exact hash, then near match)."""
    base = PastQuestion.objects.filter(duplicate_of__isnull=True, id__lt=q.id).exclude(document=q.document)
    if q.subject_id:
        base = base.filter(subject=q.subject_id)
    exact = base.filter(normalized_hash=q.normalized_hash).order_by("id").first()
    if exact:
        return exact
    candidates = base.filter(Q(year=q.year) | Q(year__isnull=True)) if q.year else base
    me = _fingerprint(q)
    best, best_score = None, 0
    for c in candidates.prefetch_related("options")[:2000]:
        score = fuzz.token_set_ratio(me, _fingerprint(c))
        if score > best_score:
            best, best_score = c, score
    return best if best_score >= NEAR_DUPLICATE_SCORE else None


def _answer_text(q) -> str | None:
    """The source's answer as normalised option TEXT (letters differ when sources reorder options)."""
    label = next((a.label for a in q.answers.all() if a.origin == "source"), None)
    if not label:
        return None
    opt = next((o for o in q.options.all() if o.label == label), None)
    return normalize(opt.text) if opt else None


def cross_source(canonical: PastQuestion) -> dict:
    """Compare answers for the same question across independent sources."""
    group = [canonical, *canonical.duplicates.select_related("source").prefetch_related("answers", "options")]
    by_source = {}
    for q in group:
        ans = _answer_text(q)
        if ans:
            by_source.setdefault(q.source_id, set()).add(ans)
    distinct_answers = {a for answers in by_source.values() for a in answers}
    return {"sources": len({q.source_id for q in group}), "sources_with_answer": len(by_source),
            "agree": len(by_source) >= 2 and len(distinct_answers) == 1,
            "conflict": len(distinct_answers) > 1, "answers": sorted(distinct_answers)}
