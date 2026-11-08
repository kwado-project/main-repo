"""Personalised roadmap engine.

A deterministic, explainable planner does the scheduling (free and instant);
the optional AI layer adds a coaching summary. Tasks are generated for a
rolling window (WINDOW_DAYS) and extended on demand, which keeps the table
small at millions of students.
"""
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.assessments.models import TopicMastery
from apps.examinations.models import StudentExam, Topic
from apps.learning.models import Lesson, LessonProgress

from .models import LearningTask, Roadmap

WINDOW_DAYS = 28
ADAPT_THRESHOLD = 0.15


def _priority_label(m):
    return "high" if m < 0.4 else "medium" if m < 0.7 else "low"


def _topic_queue(se: StudentExam):
    user = se.user
    mastery = {t.topic_id: t.mastery for t in TopicMastery.objects.filter(user=user)}
    done = set(LessonProgress.objects.filter(user=user, status="completed").values_list("lesson_id", flat=True))
    lessons = defaultdict(list)
    for l in Lesson.objects.filter(is_published=True, topic__subject__in=se.subjects.all()).order_by("order"):
        if l.id not in done:
            lessons[l.topic_id].append(l)
    items = []
    for t in Topic.objects.filter(subject__in=se.subjects.all(), is_active=True, parent__isnull=True).select_related("subject"):
        m = mastery.get(t.id)
        score = t.weight * (1 - (m if m is not None else 0.35)) + (0.3 if m is None else 0)
        items.append({"topic": t, "mastery": m if m is not None else 0.35, "score": score, "lessons": lessons[t.id]})
    items.sort(key=lambda x: -x["score"])
    return items


def _study_dates(se, start, end):
    days = set(se.study_days or range(7))
    d = start
    while d <= end:
        if d.weekday() in days:
            yield d
        d += timedelta(days=1)


def build_tasks(roadmap: Roadmap, start, end):
    se = roadmap.student_exam
    queue = _topic_queue(se)
    if not queue:
        return []
    budget = max(15, se.daily_minutes)
    exam_date = se.exam_date
    tasks, qi = [], 0
    for n, day in enumerate(_study_dates(se, start, end)):
        used, order = 0, 0
        days_to_exam = (exam_date - day).days if exam_date else 999
        if days_to_exam < 0:
            break
        if (n + 1) % 14 == 0 or days_to_exam in (7, 3):
            tasks.append(LearningTask(roadmap=roadmap, date=day, order=0, kind="mock", priority="high",
                                      title=f"Full {se.examination.name} mock examination",
                                      description="Timed, exam conditions. Review every correction afterwards.",
                                      minutes=min(budget, se.examination.mock_duration_minutes)))
            continue
        if (n + 1) % 7 == 0:
            for item in sorted(queue, key=lambda x: x["mastery"])[:2]:
                t = item["topic"]
                tasks.append(LearningTask(roadmap=roadmap, date=day, order=order, kind="revision",
                                          priority=_priority_label(item["mastery"]), subject=t.subject, topic=t,
                                          title=f"Revise {t.name}", minutes=budget // 2,
                                          description="Re-read notes, then answer a short practice set."))
                order += 1
            continue
        guard = 0
        while used < budget and guard < len(queue) * 2:
            guard += 1
            item = queue[qi % len(queue)]
            qi += 1
            t = item["topic"]
            pr = _priority_label(item["mastery"])
            if item["lessons"]:
                l = item["lessons"].pop(0)
                tasks.append(LearningTask(roadmap=roadmap, date=day, order=order, kind="lesson", priority=pr,
                                          subject=t.subject, topic=t, lesson=l, title=l.title,
                                          description=l.objective, minutes=l.estimated_minutes))
                used += l.estimated_minutes
                order += 1
            if used < budget:
                tasks.append(LearningTask(roadmap=roadmap, date=day, order=order, kind="practice", priority=pr,
                                          subject=t.subject, topic=t, title=f"Practice: {t.name}",
                                          description="20-question topic quiz with instant feedback.", minutes=15))
                used += 15
                order += 1
    LearningTask.objects.bulk_create(tasks)
    return tasks


def rules_summary(se: StudentExam) -> str:
    q = _topic_queue(se)
    weak = [i["topic"].name for i in q if i["mastery"] < 0.5][:4]
    days = (se.exam_date - timezone.localdate()).days if se.exam_date else None
    parts = []
    if days is not None:
        parts.append(f"{days} days until {se.examination.name}.")
    parts.append(f"{se.daily_minutes} minutes a day across {se.subjects.count()} subjects.")
    if weak:
        parts.append("Focus first on: " + ", ".join(weak) + ".")
    parts.append("Weekly revision days and fortnightly mock exams are built in.")
    return " ".join(parts)


@transaction.atomic
def generate_roadmap(se: StudentExam) -> Roadmap:
    prev = Roadmap.objects.select_for_update().filter(student_exam=se, is_current=True).first()
    version = (prev.version + 1) if prev else 1
    Roadmap.objects.filter(student_exam=se, is_current=True).update(is_current=False)
    start = timezone.localdate()
    end = se.exam_date or (start + timedelta(days=90))
    rm = Roadmap.objects.create(
        student_exam=se, version=version, start_date=start, end_date=end, summary=rules_summary(se),
        inputs={"daily_minutes": se.daily_minutes, "subjects": list(se.subjects.values_list("id", flat=True)),
                "exam_date": str(se.exam_date) if se.exam_date else None},
    )
    build_tasks(rm, start, min(end, start + timedelta(days=WINDOW_DAYS)))
    return rm


def ensure_window(rm: Roadmap):
    last = rm.tasks.order_by("-date").values_list("date", flat=True).first()
    today = timezone.localdate()
    if last and last < min(rm.end_date, today + timedelta(days=14)):
        build_tasks(rm, last + timedelta(days=1), min(rm.end_date, last + timedelta(days=WINDOW_DAYS)))


def complete_matching_tasks(attempt):
    se = attempt.student_exam
    if not se:
        return
    kinds = {"topic": "practice", "daily": "practice", "mock": "mock", "subject": "practice", "diagnostic": "diagnostic"}
    kind = kinds.get(attempt.kind)
    if not kind:
        return
    qs = LearningTask.objects.filter(roadmap__student_exam=se, roadmap__is_current=True, status="pending",
                                     date__lte=timezone.localdate() + timedelta(days=1))
    qs = qs.filter(kind__in=[kind, "revision"] if kind == "practice" else [kind])
    if attempt.topic_id:
        qs = qs.filter(topic_id=attempt.topic_id)
    elif attempt.subject_id and kind == "practice":
        qs = qs.filter(subject_id=attempt.subject_id)
    task = qs.order_by("date", "order").first()
    if task:
        task.status, task.completed_at = "completed", timezone.now()
        task.save(update_fields=["status", "completed_at", "updated_at"])


def complete_lesson_tasks(user, lesson):
    LearningTask.objects.filter(roadmap__student_exam__user=user, roadmap__is_current=True, lesson=lesson,
                                status="pending").update(status="completed", completed_at=timezone.now())


def adapt_after_attempt(attempt, changed: dict):
    """Re-prioritise upcoming tasks when mastery shifts meaningfully. Free."""
    se = attempt.student_exam
    if not se or not changed:
        return False
    big = {tid: after for tid, (before, after) in changed.items() if abs(after - before) >= ADAPT_THRESHOLD}
    if not big:
        return False
    rm = Roadmap.objects.filter(student_exam=se, is_current=True).first()
    if not rm:
        return False
    for tid, m in big.items():
        rm.tasks.filter(topic_id=tid, status="pending", date__gte=timezone.localdate()).update(priority=_priority_label(m))
    rm.last_adapted_at = timezone.now()
    rm.save(update_fields=["last_adapted_at"])
    return True
