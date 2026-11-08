from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.gamification import services as gami

from .models import LearningPath, Lesson, LessonProgress, NodeCompletion


def lesson_card(lesson, progress_map):
    return {"id": lesson.id, "title": lesson.title, "slug": lesson.slug, "objective": lesson.objective,
            "estimated_minutes": lesson.estimated_minutes, "xp_reward": lesson.xp_reward,
            "topic": {"id": lesson.topic_id, "name": lesson.topic.name},
            "subject": {"id": lesson.topic.subject_id, "name": lesson.topic.subject.name},
            "status": progress_map.get(lesson.id, "not_started")}


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None

    def get_queryset(self):
        qs = Lesson.objects.filter(is_published=True).select_related("topic__subject")
        if t := self.request.query_params.get("topic"):
            qs = qs.filter(topic_id=t)
        if s := self.request.query_params.get("subject"):
            qs = qs.filter(topic__subject_id=s)
        return qs

    def _progress(self, ids):
        return dict(LessonProgress.objects.filter(user=self.request.user, lesson_id__in=ids)
                    .values_list("lesson_id", "status"))

    def list(self, request):
        lessons = list(self.get_queryset()[:200])
        pm = self._progress([l.id for l in lessons])
        return Response([lesson_card(l, pm) for l in lessons])

    def retrieve(self, request, pk=None):
        lesson = self.get_queryset().filter(pk=pk).first()
        if not lesson:
            raise NotFound()
        LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        siblings = list(Lesson.objects.filter(topic=lesson.topic, is_published=True).values("id", "title", "order"))
        nxt = next((s for s in siblings if s["order"] > lesson.order), None)
        return Response({**lesson_card(lesson, self._progress([lesson.id])), "content": lesson.content,
                         "next_lesson": nxt})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        lesson = self.get_queryset().filter(pk=pk).first()
        if not lesson:
            raise NotFound()
        lp, _ = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
        first_time = lp.status != "completed"
        xp = 0
        if first_time:
            lp.status = "completed"
            lp.completed_at = timezone.now()
            lp.save(update_fields=["status", "completed_at", "updated_at"])
            xp = gami.award_xp(request.user, lesson.xp_reward, f"Lesson: {lesson.title}", f"lesson:{request.user.pk}:{lesson.pk}",
                               source_type="lesson", source_id=lesson.pk, subject=lesson.topic.subject)
            gami.bump_mission(request.user, "lessons_completed", 1)
            from apps.roadmaps.services import complete_lesson_tasks
            complete_lesson_tasks(request.user, lesson)
        streak = gami.record_activity(request.user, minutes=lesson.estimated_minutes if first_time else 0)
        new_badges = gami.check_badges(request.user)
        return Response({"xp_earned": xp, "first_time": first_time, "streak": streak.current,
                         "badges": [{"name": b.name, "icon": b.icon, "tier": b.tier} for b in new_badges]})


@api_view(["GET"])
def learning_path(request, subject_id):
    se = request.user.profile.active_student_exam
    exam_id = se.examination_id if se else None
    path = (LearningPath.objects.filter(subject_id=subject_id, examination_id=exam_id, is_published=True).first()
            or LearningPath.objects.filter(subject_id=subject_id, examination__isnull=True, is_published=True).first())
    if not path:
        return Response({"path": None, "nodes": []})
    nodes = list(path.nodes.select_related("lesson", "topic"))
    done_lessons = set(LessonProgress.objects.filter(user=request.user, status="completed",
                                                     lesson_id__in=[n.lesson_id for n in nodes if n.lesson_id])
                       .values_list("lesson_id", flat=True))
    done_nodes = set(NodeCompletion.objects.filter(user=request.user, node__in=nodes).values_list("node_id", flat=True))
    out, current_set = [], False
    for n in nodes:
        completed = (n.lesson_id in done_lessons) if n.kind == "lesson" else (n.id in done_nodes)
        if completed:
            state = "completed"
        elif not current_set:
            state, current_set = "current", True
        else:
            state = "locked"
        out.append({"id": n.id, "order": n.order, "kind": n.kind, "title": n.title, "state": state,
                    "lesson_id": n.lesson_id, "topic_id": n.topic_id, "pass_mark": n.pass_mark,
                    "estimated_minutes": n.lesson.estimated_minutes if n.lesson else 10})
    return Response({"path": {"id": path.id, "title": path.title},
                     "completed": sum(1 for n in out if n["state"] == "completed"), "total": len(out), "nodes": out})


@api_view(["GET"])
def continue_learning(request):
    """The single most useful next action for the dashboard."""
    from apps.roadmaps.models import LearningTask

    se = request.user.profile.active_student_exam
    if se:
        task = (LearningTask.objects.filter(roadmap__student_exam=se, roadmap__is_current=True, status="pending",
                                            date__lte=timezone.localdate())
                .select_related("subject", "topic", "lesson").order_by("date", "order").first())
        if task:
            return Response({"source": "roadmap", "task_id": task.id, "kind": task.kind, "title": task.title,
                             "description": task.description, "minutes": task.minutes,
                             "subject": task.subject.name if task.subject else None,
                             "subject_id": task.subject_id, "topic_id": task.topic_id, "lesson_id": task.lesson_id})
    started = (LessonProgress.objects.filter(user=request.user, status="started")
               .select_related("lesson__topic__subject").order_by("-updated_at").first())
    if started:
        l = started.lesson
        return Response({"source": "lesson", "kind": "lesson", "title": l.title, "description": l.objective,
                         "minutes": l.estimated_minutes, "subject": l.topic.subject.name,
                         "subject_id": l.topic.subject_id, "topic_id": l.topic_id, "lesson_id": l.id})
    return Response({"source": "none"})
