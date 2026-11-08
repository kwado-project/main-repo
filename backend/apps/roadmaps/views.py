from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.core.exceptions import InsufficientCredits
from apps.examinations.models import StudentExam
from apps.wallet.services import get_wallet, price_of

from . import services
from .models import LearningTask, Roadmap
from .tasks import ai_roadmap_summary


def _se(request):
    sid = request.query_params.get("student_exam") or (
        request.data.get("student_exam") if request.method == "POST" else None)
    if sid:
        se = StudentExam.objects.filter(pk=sid, user=request.user).first()
    else:
        se = request.user.profile.active_student_exam
    if not se:
        raise NotFound("No active examination.")
    return se


def _task(t):
    today = timezone.localdate()
    state = t.status if t.status != "pending" else ("overdue" if t.date < today else "current" if t.date == today else "upcoming")
    return {"id": t.id, "date": t.date, "kind": t.kind, "title": t.title, "description": t.description,
            "minutes": t.minutes, "priority": t.priority, "status": t.status, "state": state,
            "subject": {"id": t.subject_id, "name": t.subject.name, "color": t.subject.color} if t.subject else None,
            "topic_id": t.topic_id, "lesson_id": t.lesson_id}


@api_view(["GET"])
def current(request):
    se = _se(request)
    rm = Roadmap.objects.filter(student_exam=se, is_current=True).first()
    if not rm:
        return Response({"roadmap": None, "cost": price_of("ai_roadmap")})
    services.ensure_window(rm)
    tasks = list(rm.tasks.select_related("subject"))
    done = sum(1 for t in tasks if t.status == "completed")
    return Response({
        "roadmap": {"id": rm.id, "version": rm.version, "summary": rm.summary, "ai_summary": rm.ai_summary,
                    "start_date": rm.start_date, "end_date": rm.end_date, "exam_date": se.exam_date,
                    "last_adapted_at": rm.last_adapted_at},
        "stats": {"completed": done, "total": len(tasks),
                  "overdue": sum(1 for t in tasks if t.status == "pending" and t.date < timezone.localdate())},
        "tasks": [_task(t) for t in tasks],
        "cost": price_of("ai_roadmap"),
    })


@api_view(["POST"])
def generate(request):
    se = _se(request)
    cost = price_of("ai_roadmap")
    if get_wallet(request.user).balance < cost:
        raise InsufficientCredits()
    rm = services.generate_roadmap(se)
    ai_roadmap_summary.delay(rm.id)
    if se.onboarding_step != "done":
        se.onboarding_step = "done"
        se.save(update_fields=["onboarding_step"])
        prof = request.user.profile
        prof.onboarding_completed = True
        prof.active_student_exam = se
        prof.save(update_fields=["onboarding_completed", "active_student_exam"])
    return Response({"id": rm.id}, status=201)


@api_view(["POST"])
def update_task(request, task_id):
    t = LearningTask.objects.filter(pk=task_id, roadmap__student_exam__user=request.user).first()
    if not t:
        raise NotFound()
    status = request.data.get("status")
    if status not in ("completed", "skipped", "pending"):
        return Response({"detail": "Invalid status."}, status=400)
    t.status = status
    t.completed_at = timezone.now() if status == "completed" else None
    t.save(update_fields=["status", "completed_at", "updated_at"])
    return Response(_task(t))
