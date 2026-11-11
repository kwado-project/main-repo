"""Optional AI second opinion on answer keys. Advisory only: it adds an AI answer claim and a
verification record, and can push a question to human review — it never changes the source answer."""
import json
import re

from apps.core.services import ai

SYSTEM = (
    "You check multiple-choice questions from Nigerian JAMB UTME past papers for errors. "
    "Work the question out yourself, then reply with ONLY a JSON object: "
    '{"answer": "<A-E or null if no option is correct>", "confidence": <0-1>, '
    '"issues": ["<short problems: ambiguous wording, typo in options, missing diagram, more than one correct option, etc.>"]}. '
    "Do not explain outside the JSON."
)


def review(q) -> dict:
    opts = "\n".join(f"{o.label}. {o.text}" for o in q.options.all())
    passage = f"Passage:\n{q.passage}\n\n" if q.passage else ""
    prompt = f"Subject: {q.subject.name if q.subject_id else 'unknown'}\n{passage}Question: {q.text}\n{opts}"
    result = ai.complete(purpose="research_review", system=SYSTEM, messages=[{"role": "user", "content": prompt}])
    m = re.search(r"\{.*\}", result.text, re.S)
    data = json.loads(m.group(0)) if m else {}
    answer = str(data.get("answer") or "").strip().upper()[:1] or None
    return {"answer": answer, "confidence": float(data.get("confidence") or 0), "issues": list(data.get("issues") or [])[:5],
            "model": result.model, "is_mock": result.is_mock}
