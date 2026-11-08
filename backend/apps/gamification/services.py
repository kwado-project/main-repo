"""XP, levels, streaks, missions, badges and leaderboards."""
from datetime import date, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.accounts.models import StudentProfile
from apps.notifications.models import notify

from .models import ActivityDay, Badge, Mission, StudentBadge, StudentMission, Streak, XPTransaction

# Level n requires 50*n*(n-1) total XP: L2=100, L3=300, L4=600, L5=1000 …


def level_for_xp(xp: int) -> int:
    n = 1
    while 50 * (n + 1) * n <= xp:
        n += 1
    return n


def level_bounds(level: int):
    return 50 * level * (level - 1), 50 * (level + 1) * level


def award_xp(user, amount: int, reason: str, key: str, *, source_type="", source_id="", subject=None) -> int:
    """Idempotent XP award. Returns XP actually added (0 if replayed)."""
    if amount <= 0:
        return 0
    try:
        with transaction.atomic():
            XPTransaction.objects.create(
                user=user, amount=amount, reason=reason, idempotency_key=key,
                source_type=source_type, source_id=str(source_id), subject=subject,
            )
            StudentProfile.objects.filter(user=user).update(total_xp=F("total_xp") + amount)
            prof = StudentProfile.objects.select_for_update().get(user=user)
            new_level = level_for_xp(prof.total_xp)
            if new_level != prof.level:
                leveled_up = new_level > prof.level
                prof.level = new_level
                prof.save(update_fields=["level"])
                if leveled_up:
                    notify(user, "achievement", f"Level {new_level} reached!", "Keep the momentum going.", "/app/achievements")
            today = timezone.localdate()
            day, _ = ActivityDay.objects.get_or_create(user=user, date=today)
            ActivityDay.objects.filter(pk=day.pk).update(xp=F("xp") + amount)
    except IntegrityError:
        return 0
    leaderboard_add(user, amount, subject_id=getattr(subject, "id", None))
    bump_mission(user, "xp_earned", amount)
    return amount


def record_activity(user, *, questions=0, minutes=0):
    """Mark today active, extend the streak, and count activity."""
    today = timezone.localdate()
    day, _ = ActivityDay.objects.get_or_create(user=user, date=today)
    if questions or minutes:
        ActivityDay.objects.filter(pk=day.pk).update(
            questions_answered=F("questions_answered") + questions, minutes=F("minutes") + minutes
        )
    return touch_streak(user, today)


def touch_streak(user, today: date | None = None) -> Streak:
    today = today or timezone.localdate()
    with transaction.atomic():
        streak, _ = Streak.objects.select_for_update().get_or_create(user=user)
        last = streak.last_active_date
        if last == today:
            return streak
        if last == today - timedelta(days=1):
            streak.current += 1
        elif last == today - timedelta(days=2) and streak.freezes_available > 0:
            streak.freezes_available -= 1  # a streak freeze covers one missed day
            streak.current += 1
        else:
            streak.current = 1
        streak.last_active_date = today
        streak.longest = max(streak.longest, streak.current)
        if streak.current in (7, 30, 100):
            notify(user, "streak", f"{streak.current}-day streak!", "You're building a powerful habit.", "/app")
        if streak.current % 7 == 0 and streak.freezes_available < 2:
            streak.freezes_available += 1
        streak.save()
    check_badges(user)
    return streak


def effective_streak(streak: Streak) -> int:
    """Current streak as displayed (0 if the student already missed a day)."""
    if not streak.last_active_date:
        return 0
    gap = (timezone.localdate() - streak.last_active_date).days
    if gap <= 1 or (gap == 2 and streak.freezes_available > 0):
        return streak.current
    return 0


# ----------------------------------------------------------------------------
# Missions
# ----------------------------------------------------------------------------
def period_start(period: str, today: date | None = None) -> date:
    today = today or timezone.localdate()
    return today if period == "daily" else today - timedelta(days=today.weekday())


def missions_for(user):
    out = []
    for m in Mission.objects.filter(is_active=True):
        sm, _ = StudentMission.objects.get_or_create(user=user, mission=m, period_start=period_start(m.period))
        out.append(sm)
    return out


def bump_mission(user, metric: str, amount: int = 1):
    for m in Mission.objects.filter(is_active=True, metric=metric):
        ps = period_start(m.period)
        sm, _ = StudentMission.objects.get_or_create(user=user, mission=m, period_start=ps)
        if sm.completed_at:
            continue
        StudentMission.objects.filter(pk=sm.pk).update(progress=F("progress") + amount)
        sm.refresh_from_db()
        if sm.progress >= m.target:
            updated = StudentMission.objects.filter(pk=sm.pk, completed_at__isnull=True).update(completed_at=timezone.now())
            if updated:
                award_xp(user, m.xp_reward, f"Mission: {m.title}", f"mission:{sm.pk}", source_type="mission",
                         source_id=sm.pk)


# ----------------------------------------------------------------------------
# Badges
# ----------------------------------------------------------------------------
def _metric(user, kind):
    from apps.assessments.models import QuizAttempt, TopicMastery
    from apps.learning.models import LessonProgress

    if kind == "streak":
        return Streak.objects.filter(user=user).values_list("longest", flat=True).first() or 0
    if kind == "lessons":
        return LessonProgress.objects.filter(user=user, status="completed").count()
    if kind == "quizzes":
        return QuizAttempt.objects.filter(user=user, status="submitted").count()
    if kind == "perfect_quizzes":
        return QuizAttempt.objects.filter(user=user, status="submitted", score_percent=100, total_questions__gte=5).count()
    if kind == "xp":
        return StudentProfile.objects.filter(user=user).values_list("total_xp", flat=True).first() or 0
    if kind == "mastered_topics":
        return TopicMastery.objects.filter(user=user, mastery__gte=0.85, attempts__gte=10).count()
    if kind == "mock_score":
        best = QuizAttempt.objects.filter(user=user, kind="mock", status="submitted").order_by("-score_percent").first()
        return float(best.score_percent) if best else 0
    return 0


def check_badges(user):
    owned = set(StudentBadge.objects.filter(user=user).values_list("badge_id", flat=True))
    new = []
    for b in Badge.objects.exclude(id__in=owned):
        kind, value = b.criteria.get("type"), b.criteria.get("value", 0)
        if kind and _metric(user, kind) >= value:
            try:
                StudentBadge.objects.create(user=user, badge=b)
            except IntegrityError:
                continue
            new.append(b)
            notify(user, "achievement", f"Badge unlocked: {b.name}", b.description, "/app/achievements")
            award_xp(user, b.xp_reward, f"Badge: {b.name}", f"badge:{user.pk}:{b.pk}", source_type="badge", source_id=b.pk)
    return new


# ----------------------------------------------------------------------------
# Leaderboards — Redis sorted sets, with a DB fallback.
# ----------------------------------------------------------------------------
def _redis():
    try:
        from django_redis import get_redis_connection

        return get_redis_connection("default")
    except Exception:
        return None


def _lb_keys(subject_id=None):
    today = timezone.localdate()
    y, w, _ = today.isocalendar()
    keys = {"daily": f"kwado:lb:daily:{today:%Y%m%d}", "weekly": f"kwado:lb:weekly:{y}{w:02d}"}
    if subject_id:
        keys["subject"] = f"kwado:lb:subject:{subject_id}:{y}{w:02d}"
    return keys


def leaderboard_add(user, amount, subject_id=None):
    r = _redis()
    if not r:
        return
    try:
        pipe = r.pipeline()
        for name, key in _lb_keys(subject_id).items():
            pipe.zincrby(key, amount, user.pk)
            pipe.expire(key, 60 * 60 * 24 * (2 if name == "daily" else 15))
        pipe.execute()
    except Exception:
        pass


def leaderboard(period: str, user, subject_id=None, limit=50):
    cache_key = f"lb:{period}:{subject_id}:{timezone.localdate()}"
    rows = cache.get(cache_key)
    if rows is None:
        rows = _leaderboard_rows(period, subject_id, limit)
        cache.set(cache_key, rows, 30)
    hidden = set(StudentProfile.objects.filter(
        user_id__in=[r[0] for r in rows], leaderboard_visibility="hidden").values_list("user_id", flat=True))
    profiles = {p.user_id: p for p in StudentProfile.objects.filter(user_id__in=[r[0] for r in rows]).select_related("user")}
    out, rank = [], 0
    for uid, xp in rows:
        if uid in hidden or uid not in profiles:
            continue
        rank += 1
        p = profiles[uid]
        out.append({"rank": rank, "name": p.public_name(), "xp": int(xp), "level": p.level,
                    "avatar_color": p.avatar_color, "is_me": uid == user.pk})
    me = next((r for r in out if r["is_me"]), None)
    return {"period": period, "entries": out, "me": me}


def _leaderboard_rows(period, subject_id, limit):
    r = _redis()
    key = _lb_keys(subject_id).get("subject" if period == "subject" else period)
    if r and key:
        try:
            return [(int(uid), score) for uid, score in r.zrevrange(key, 0, limit * 2, withscores=True)]
        except Exception:
            pass
    today = timezone.localdate()
    since = today if period == "daily" else today - timedelta(days=today.weekday())
    qs = XPTransaction.objects.filter(created_at__date__gte=since)
    if period == "subject" and subject_id:
        qs = qs.filter(subject_id=subject_id)
    return [(row["user_id"], row["xp"]) for row in
            qs.values("user_id").annotate(xp=Sum("amount")).order_by("-xp")[: limit * 2]]
