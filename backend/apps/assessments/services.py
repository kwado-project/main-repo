"""Assessment engine.

Marking always uses the verified AnswerKey — never the AI. Scores are computed
on the server only.
"""
import random
from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.examinations.models import StudentExam, Subject, Topic
from apps.gamification import services as gami
from apps.questions.models import AnswerKey, Question
from apps.wallet import services as wallet

from .models import QuizAttempt, StudentAnswer, TopicMastery


@dataclass(frozen=True)
class KindConfig:
    questions: int
    activity: str | None
    mode: str
    minutes: int | None
    min_questions: int


KINDS = {
    "daily": KindConfig(10, "daily_practice", "practice", None, 3),
    "topic": KindConfig(20, "topic_quiz", "practice", None, 5),
    "subject": KindConfig(40, "subject_assessment", "exam", 45, 10),
    "mock": KindConfig(40, "mock_exam", "exam", 120, 10),  # 40 per subject
    "diagnostic": KindConfig(8, "diagnostic", "exam", 30, 4),  # 8 per subject
    "lesson": KindConfig(5, None, "practice", None, 1),
    "challenge": KindConfig(10, None, "practice", None, 3),
}

MASTERY_ALPHA = 0.25
PASS_MARK = 70


def _pool(subject_id: int, topic_id: int | None, exam_id: int | None) -> list[int]:
    key = f"qpool:{subject_id}:{topic_id}:{exam_id}"
    ids = cache.get(key)
    if ids is None:
        qs = Question.objects.filter(subject_id=subject_id, status=Question.Status.PUBLISHED)
        if topic_id:
            qs = qs.filter(topic_id__in=[topic_id, *Topic.objects.filter(parent_id=topic_id).values_list("id", flat=True)])
        if exam_id:
            from django.db.models import Q
            qs = qs.filter(Q(examination_id=exam_id) | Q(examination__isnull=True))
        ids = list(qs.values_list("id", flat=True)[:5000])
        cache.set(key, ids, 600)
    return ids


def _recent_ids(user, days=3) -> set[int]:
    since = timezone.now() - timedelta(days=days)
    return set(StudentAnswer.objects.filter(attempt__user=user, attempt__created_at__gte=since)
               .values_list("question_id", flat=True)[:2000])


def select_questions(user, *, kind, student_exam, subject, topic, lesson) -> list[int]:
    cfg = KINDS[kind]
    exam_id = student_exam.examination_id if student_exam else None
    recent = _recent_ids(user)

    def pick(subject_id, topic_id, n):
        pool = _pool(subject_id, topic_id, exam_id)
        fresh = [i for i in pool if i not in recent]
        chosen = random.sample(fresh, min(n, len(fresh)))
        if len(chosen) < n:  # top up with previously seen questions
            rest = [i for i in pool if i not in set(chosen)]
            chosen += random.sample(rest, min(n - len(chosen), len(rest)))
        return chosen

    if kind in ("mock", "diagnostic"):
        if not student_exam:
            raise ValidationError({"student_exam": "Choose an examination first."})
        ids = []
        for s in student_exam.subjects.all():
            ids += pick(s.id, None, cfg.questions)
        return ids
    if kind == "lesson" and lesson:
        return pick(lesson.topic.subject_id, lesson.topic_id, cfg.questions)
    if not subject:
        raise ValidationError({"subject": "Choose a subject."})
    if kind == "daily" and not topic:
        # Bias daily practice towards the student's weakest topics.
        weak = list(TopicMastery.objects.filter(user=user, subject=subject, mastery__lt=0.6)
                    .order_by("mastery").values_list("topic_id", flat=True)[:3])
        ids = []
        for t in weak:
            ids += pick(subject.id, t, 3)
        ids = list(dict.fromkeys(ids))
        ids += [i for i in pick(subject.id, None, cfg.questions) if i not in ids][: cfg.questions - len(ids)]
        return ids[: cfg.questions]
    return pick(subject.id, topic.id if topic else None, cfg.questions)


def start_attempt(user, *, kind, student_exam=None, subject=None, topic=None, lesson=None, mode=None,
                  idempotency_key=None) -> QuizAttempt:
    if kind not in KINDS:
        raise ValidationError({"kind": "Unknown assessment type."})
    cfg = KINDS[kind]
    if student_exam and student_exam.user_id != user.id:
        raise ValidationError({"student_exam": "Not found."})
    if subject and student_exam and not student_exam.subjects.filter(id=subject.id).exists():
        raise ValidationError({"subject": "This subject is not part of your selected examination."})
    if topic and subject and topic.subject_id != subject.id:
        raise ValidationError({"topic": "Topic does not belong to this subject."})

    if idempotency_key:
        existing = QuizAttempt.objects.filter(user=user, result_summary__client_key=idempotency_key).first()
        if existing:
            return existing

    qids = select_questions(user, kind=kind, student_exam=student_exam, subject=subject, topic=topic, lesson=lesson)
    if len(qids) < cfg.min_questions:
        # Fail BEFORE charging: the student is never billed for an empty quiz.
        raise ValidationError({"detail": "There aren't enough verified questions for this selection yet. "
                                         "Try another topic — you have not been charged.",
                               "code": "not_enough_questions"})
    mode = mode if mode in ("practice", "exam") and kind not in ("mock", "diagnostic") else cfg.mode
    n_subjects = student_exam.subjects.count() if (student_exam and kind in ("mock", "diagnostic")) else 1
    limit = cfg.minutes * 60 * (n_subjects if kind == "diagnostic" else 1) if cfg.minutes else None
    if kind == "mock" and student_exam:
        limit = student_exam.examination.mock_duration_minutes * 60

    with transaction.atomic():
        attempt = QuizAttempt.objects.create(
            user=user, student_exam=student_exam, kind=kind, mode=mode, subject=subject, topic=topic, lesson=lesson,
            time_limit_seconds=limit, total_questions=len(qids),
            hearts_enabled=kind == "challenge", hearts_remaining=3 if kind == "challenge" else 0,
            result_summary={"client_key": idempotency_key} if idempotency_key else {},
        )
        StudentAnswer.objects.bulk_create(
            [StudentAnswer(attempt=attempt, question_id=q, order=i) for i, q in enumerate(qids)]
        )
        if cfg.activity:
            charge = wallet.charge_activity(user, cfg.activity, f"attempt:{attempt.pk}",
                                            reference_type="quiz_attempt", reference_id=str(attempt.pk))
            attempt.credits_charged = charge.credits
            attempt.charge_transaction = charge.transaction
            attempt.save(update_fields=["credits_charged", "charge_transaction"])
    return attempt


def _deadline_passed(attempt) -> bool:
    if not attempt.time_limit_seconds:
        return False
    grace = 30
    return timezone.now() > attempt.started_at + timedelta(seconds=attempt.time_limit_seconds + grace)


def answer(attempt: QuizAttempt, question_id: int, option_id: int | None, time_spent: int = 0) -> StudentAnswer:
    if attempt.status != QuizAttempt.Status.IN_PROGRESS:
        raise ValidationError({"detail": "This assessment has already been submitted."})
    if _deadline_passed(attempt):
        raise ValidationError({"detail": "Time is up for this assessment.", "code": "time_up"})
    with transaction.atomic():
        sa = (StudentAnswer.objects.select_for_update().select_related("question")
              .filter(attempt=attempt, question_id=question_id).first())
        if not sa:
            raise ValidationError({"question": "Question is not part of this assessment."})
        if option_id is not None and not sa.question.options.filter(id=option_id).exists():
            raise ValidationError({"option": "Invalid option."})
        if attempt.mode == "practice" and sa.selected_option_id:
            return sa  # practice answers lock once revealed
        if attempt.hearts_enabled and attempt.hearts_remaining == 0:
            raise ValidationError({"detail": "You're out of hearts. Submit to see your results.", "code": "no_hearts"})
        sa.selected_option_id = option_id
        sa.answered_at = timezone.now()
        sa.time_spent_seconds = min(max(0, int(time_spent or 0)), 3600)
        key = AnswerKey.objects.filter(question_id=question_id).values_list("correct_option_id", flat=True).first()
        sa.is_correct = (key is not None and option_id == key)
        sa.save()
        if attempt.hearts_enabled and not sa.is_correct:
            QuizAttempt.objects.filter(pk=attempt.pk).update(hearts_remaining=max(0, attempt.hearts_remaining - 1))
            attempt.hearts_remaining = max(0, attempt.hearts_remaining - 1)
    return sa


def _update_mastery(user, answers):
    by_topic = {}
    for sa in answers:
        if not sa.question.topic_id or sa.selected_option_id is None:
            continue
        by_topic.setdefault(sa.question.topic_id, []).append(bool(sa.is_correct))
    weak_before = set()
    changed = {}
    for topic_id, results in by_topic.items():
        tm, _ = TopicMastery.objects.select_for_update().get_or_create(
            user=user, topic_id=topic_id, defaults={"subject_id": answers[0].question.subject_id})
        before = tm.mastery
        if tm.attempts and before < 0.5:
            weak_before.add(topic_id)
        m = before if tm.attempts else (sum(results) / len(results))
        for r in results:
            m = m + MASTERY_ALPHA * ((1.0 if r else 0.0) - m)
        tm.mastery = round(m, 4)
        tm.attempts += len(results)
        tm.correct += sum(results)
        tm.last_practised_at = timezone.now()
        tm.save()
        changed[topic_id] = (before, tm.mastery)
    return weak_before, changed


def submit(attempt: QuizAttempt) -> QuizAttempt:
    with transaction.atomic():
        attempt = QuizAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.status == QuizAttempt.Status.SUBMITTED:
            return attempt
        answers = list(attempt.answers.select_related("question__topic", "question__subject"))
        keys = dict(AnswerKey.objects.filter(question_id__in=[a.question_id for a in answers])
                    .values_list("question_id", "correct_option_id"))
        for a in answers:  # re-mark everything from the answer key at submission
            a.is_correct = a.selected_option_id is not None and keys.get(a.question_id) == a.selected_option_id
        StudentAnswer.objects.bulk_update(answers, ["is_correct"])
        correct = sum(1 for a in answers if a.is_correct)
        answered = sum(1 for a in answers if a.selected_option_id)
        total = len(answers)
        attempt.status = QuizAttempt.Status.SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.correct_count = correct
        attempt.score_percent = round(100 * correct / total, 2) if total else 0
        attempt.time_spent_seconds = int((attempt.submitted_at - attempt.started_at).total_seconds())
        if attempt.time_limit_seconds:
            attempt.time_spent_seconds = min(attempt.time_spent_seconds, attempt.time_limit_seconds)

        weak_before, changed = _update_mastery(attempt.user, answers)

        topics = {}
        for a in answers:
            t = a.question.topic
            name = t.name if t else "General"
            row = topics.setdefault(name, {"topic_id": t.id if t else None, "subject": a.question.subject.name,
                                           "correct": 0, "total": 0})
            row["total"] += 1
            row["correct"] += 1 if a.is_correct else 0
        breakdown = sorted(
            [{"topic": k, **v, "percent": round(100 * v["correct"] / v["total"])} for k, v in topics.items()],
            key=lambda r: r["percent"])
        weak = [r for r in breakdown if r["percent"] < 60][:5]
        subjects = {}
        for a in answers:
            s = subjects.setdefault(a.question.subject.name, {"correct": 0, "total": 0})
            s["total"] += 1
            s["correct"] += 1 if a.is_correct else 0

        xp = correct * 2 + (10 if answered >= max(1, total // 2) else 0)
        if total >= 5 and correct == total:
            xp += 20
        if attempt.kind == "mock":
            xp += 30
        attempt.result_summary = {
            **attempt.result_summary,
            "answered": answered, "incorrect": answered - correct, "skipped": total - answered,
            "topics": breakdown, "weak_topics": weak,
            "subjects": [{"subject": k, **v, "percent": round(100 * v["correct"] / v["total"])} for k, v in subjects.items()],
            "recommendations": _recommendations(attempt, weak),
        }
        attempt.save()

    gained = gami.award_xp(attempt.user, xp, f"{attempt.get_kind_display()} completed", f"attempt:{attempt.pk}",
                           source_type="quiz_attempt", source_id=attempt.pk, subject=attempt.subject)
    QuizAttempt.objects.filter(pk=attempt.pk).update(xp_earned=gained)
    attempt.xp_earned = gained
    gami.record_activity(attempt.user, questions=answered, minutes=attempt.time_spent_seconds // 60)
    gami.bump_mission(attempt.user, "questions_answered", answered)
    gami.bump_mission(attempt.user, "correct_answers", correct)
    gami.bump_mission(attempt.user, "quizzes_completed", 1)
    if weak_before:
        gami.bump_mission(attempt.user, "weak_topic_practice", 1)
    gami.check_badges(attempt.user)
    _complete_path_nodes(attempt)
    from apps.roadmaps.services import adapt_after_attempt, complete_matching_tasks

    complete_matching_tasks(attempt)
    adapt_after_attempt(attempt, changed)
    return attempt


def _recommendations(attempt, weak):
    recs = []
    for w in weak[:3]:
        recs.append({"type": "topic_quiz", "label": f"Practise {w['topic']}", "topic_id": w["topic_id"],
                     "reason": f"You scored {w['percent']}% on {w['topic']}."})
    if attempt.kind in ("daily", "topic") and not weak:
        recs.append({"type": "subject", "label": "Try a timed subject assessment",
                     "reason": "You're doing well — test yourself under exam conditions."})
    recs.append({"type": "tutor", "label": "Ask the AI tutor about your mistakes",
                 "reason": "Get step-by-step explanations for anything unclear."})
    return recs


def _complete_path_nodes(attempt):
    from apps.learning.models import LearningPathNode, NodeCompletion

    if attempt.kind not in ("challenge", "lesson") or not attempt.topic_id:
        return
    score = int(attempt.score_percent or 0)
    kinds = ["challenge", "boss"] if attempt.kind == "challenge" else []
    for node in LearningPathNode.objects.filter(topic_id=attempt.topic_id, kind__in=kinds):
        if score >= node.pass_mark:
            nc, _ = NodeCompletion.objects.get_or_create(user=attempt.user, node=node)
            if score > nc.best_score:
                nc.best_score = score
                nc.save(update_fields=["best_score"])


def subject_progress(user, student_exam: StudentExam):
    out = []
    for s in student_exam.subjects.all():
        topics = Topic.objects.filter(subject=s, is_active=True, parent__isnull=True)
        n_topics = topics.count() or 1
        tms = {tm.topic_id: tm for tm in TopicMastery.objects.filter(user=user, subject=s)}
        mastery = sum(tm.mastery for tm in tms.values()) / n_topics
        out.append({
            "subject": {"id": s.id, "name": s.name, "icon": s.icon, "color": s.color, "slug": s.slug},
            "mastery": round(mastery * 100),
            "topics_practised": len(tms), "topics_total": n_topics,
            "level": "Mastered" if mastery >= .85 else "Proficient" if mastery >= .65 else
                     "Developing" if mastery >= .4 else "Beginner" if tms else "Not started",
        })
    return out
