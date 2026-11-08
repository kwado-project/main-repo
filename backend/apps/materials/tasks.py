import base64

from celery import shared_task

from apps.core.services import ai, storage
from apps.notifications.models import notify
from apps.wallet.services import paid_activity

from .extract import chunk, extract_text
from .models import MaterialChunk, StudyMaterial

ANALYSIS_SYSTEM = (
    "You are Kwado AI's study assistant. Analyse the student's uploaded study material and return Markdown with: "
    "## Summary (5 bullets), ## Key concepts (with one-line definitions), ## Likely exam angles, "
    "## 5 self-test questions (answers at the end, labelled 'Kwado practice questions'). Use LaTeX for maths. "
    "Only use what's in the material; say if it is unclear or incomplete. Never claim questions are official past questions."
)


@shared_task
def process_material(material_id: int):
    """Extract text and build retrieval embeddings (free for the student)."""
    m = StudyMaterial.objects.get(pk=material_id)
    StudyMaterial.objects.filter(pk=m.pk).update(status="processing")
    try:
        data = storage.get_object(m.storage_key)
        ext = "." + m.filename.rsplit(".", 1)[-1].lower()
        text = extract_text(data, ext)
        pieces = [c for c in chunk(text) if c.strip()][:400]
        if pieces:
            vectors = []
            for i in range(0, len(pieces), 64):
                vectors += ai.embed(pieces[i:i + 64])
            MaterialChunk.objects.filter(material=m).delete()
            MaterialChunk.objects.bulk_create(
                [MaterialChunk(material=m, index=i, text=t, embedding=v) for i, (t, v) in enumerate(zip(pieces, vectors))])
        StudyMaterial.objects.filter(pk=m.pk).update(status="ready", extracted_chars=len(text), error="")
    except Exception as e:  # noqa: BLE001
        StudyMaterial.objects.filter(pk=m.pk).update(status="failed", error=str(e)[:255])


@shared_task
def analyse_material(material_id: int, idem: str):
    m = StudyMaterial.objects.select_related("owner", "subject").get(pk=material_id)
    text = "\n".join(m.chunks.order_by("index").values_list("text", flat=True))[:60000]
    if text.strip():
        content = f"Material title: {m.title}\nSubject: {m.subject.name if m.subject else 'unspecified'}\n\n{text}"
    elif m.content_type.startswith("image/"):
        data = storage.get_object(m.storage_key)
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": m.content_type,
                                          "data": base64.standard_b64encode(data).decode()}},
            {"type": "text", "text": f"Material title: {m.title}. Analyse this image of study notes."},
        ]
    else:
        StudyMaterial.objects.filter(pk=m.pk).update(error="No readable text found in this file.")
        return
    try:
        with paid_activity(m.owner, "document_analysis", f"material:{m.pk}:{idem}",
                           reference_type="material", reference_id=str(m.pk)):
            result = ai.complete(purpose="document_analysis", system=ANALYSIS_SYSTEM,
                                 messages=[{"role": "user", "content": content}])
    except ai.AIError:
        StudyMaterial.objects.filter(pk=m.pk).update(error="Analysis failed — your credits were refunded.")
        notify(m.owner, "material", "Analysis didn't complete", "Your credits were refunded.", f"/app/materials")
        return
    StudyMaterial.objects.filter(pk=m.pk).update(analysis=result.text, analysis_charged=True, error="")
    notify(m.owner, "material", "Your document analysis is ready", m.title, "/app/materials")
