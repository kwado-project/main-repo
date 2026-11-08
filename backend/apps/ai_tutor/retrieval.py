from django.db.models import Q
from pgvector.django import CosineDistance

from apps.core.services.ai import embed
from apps.materials.models import MaterialChunk


def retrieve(user, query: str, subject_id=None, k=4, max_chars=4000) -> str:
    """Top-k chunks from the student's own materials and approved platform sources."""
    try:
        vec = embed([query], input_type="query")[0]
    except Exception:
        return ""
    qs = MaterialChunk.objects.filter(material__status="ready").filter(
        Q(material__owner=user) | Q(material__visibility="approved"))
    if subject_id:
        qs = qs.filter(Q(material__subject_id=subject_id) | Q(material__subject__isnull=True))
    rows = (qs.annotate(d=CosineDistance("embedding", vec)).filter(d__lt=0.75).order_by("d")
            .select_related("material")[:k])
    out, total = [], 0
    for c in rows:
        snippet = c.text[:1200]
        total += len(snippet)
        if total > max_chars:
            break
        label = "Approved syllabus/source" if c.material.visibility == "approved" else "Student's own notes"
        out.append(f"[{label}: {c.material.title}]\n{snippet}")
    return "\n\n".join(out)
