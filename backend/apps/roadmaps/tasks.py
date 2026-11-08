from celery import shared_task

from apps.core.services import ai
from apps.wallet.services import paid_activity

from .models import Roadmap

SYSTEM = (
    "You are Kwado AI's study coach for Nigerian secondary-school students preparing for national examinations. "
    "Write a warm, specific, motivating study-plan summary in under 180 words, in British English, using short "
    "Markdown bullet points. Only refer to subjects, topics and numbers given in the context. Never invent "
    "examination dates, official questions, or statistics."
)


@shared_task
def ai_roadmap_summary(roadmap_id: int):
    rm = Roadmap.objects.select_related("student_exam__user", "student_exam__examination").get(pk=roadmap_id)
    se = rm.student_exam
    tasks = list(rm.tasks.select_related("topic")[:40])
    ctx = (f"Exam: {se.examination.name}; date: {se.exam_date}; daily minutes: {se.daily_minutes}.\n"
           f"Planner notes: {rm.summary}\nFirst tasks: " + "; ".join(f"{t.date} {t.title} ({t.priority})" for t in tasks))
    try:
        with paid_activity(se.user, "ai_roadmap", f"roadmap:{rm.pk}", reference_type="roadmap", reference_id=str(rm.pk)):
            result = ai.complete(purpose="roadmap", system=SYSTEM, context="",
                                 messages=[{"role": "user", "content": ctx + "\n\nWrite my study plan summary."}])
    except ai.AIError:
        return  # refunded automatically; the rules-based summary remains
    rm.ai_summary = result.text
    rm.save(update_fields=["ai_summary"])
