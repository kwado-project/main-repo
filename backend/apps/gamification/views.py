from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

from .models import ActivityDay, Badge, StudentBadge, Streak, XPTransaction
from .services import (effective_streak, leaderboard, level_bounds, missions_for)


@api_view(["GET"])
def summary(request):
    user = request.user
    prof = user.profile
    streak, _ = Streak.objects.get_or_create(user=user)
    lo, hi = level_bounds(prof.level)
    today = timezone.localdate()
    start = today - timedelta(days=today.weekday())
    days = {d.date: d for d in ActivityDay.objects.filter(user=user, date__gte=start - timedelta(days=21))}
    week = [{"date": (start + timedelta(days=i)).isoformat(),
             "xp": days[start + timedelta(days=i)].xp if (start + timedelta(days=i)) in days else 0,
             "active": (start + timedelta(days=i)) in days}
            for i in range(7)]
    heat = [{"date": (today - timedelta(days=i)).isoformat(),
             "xp": days[today - timedelta(days=i)].xp if (today - timedelta(days=i)) in days else 0}
            for i in range(27, -1, -1)]
    return Response({
        "xp": prof.total_xp, "level": prof.level, "level_floor": lo, "level_ceiling": hi,
        "streak": {"current": effective_streak(streak), "longest": streak.longest,
                   "freezes": streak.freezes_available,
                   "active_today": streak.last_active_date == today},
        "week": week, "heatmap": heat,
        "today_xp": days[today].xp if today in days else 0,
        "daily_goal_xp": max(20, prof.daily_goal_minutes),
    })


@api_view(["GET"])
def missions(request):
    out = []
    for sm in missions_for(request.user):
        m = sm.mission
        out.append({"id": sm.id, "title": m.title, "period": m.period, "metric": m.metric, "icon": m.icon,
                    "target": m.target, "progress": min(sm.progress, m.target), "xp_reward": m.xp_reward,
                    "completed": bool(sm.completed_at)})
    return Response(out)


@api_view(["GET"])
def badges(request):
    earned = {sb.badge_id: sb for sb in StudentBadge.objects.filter(user=request.user)}
    out = [{"slug": b.slug, "name": b.name, "description": b.description, "icon": b.icon, "tier": b.tier,
            "xp_reward": b.xp_reward, "earned": b.id in earned,
            "earned_at": earned[b.id].earned_at if b.id in earned else None,
            "seen": earned[b.id].seen if b.id in earned else True}
           for b in Badge.objects.all()]
    return Response(out)


@api_view(["POST"])
def badges_seen(request):
    StudentBadge.objects.filter(user=request.user, seen=False).update(seen=True)
    return Response(status=204)


@api_view(["GET"])
def leaderboard_view(request):
    period = request.query_params.get("period", "weekly")
    if period not in ("daily", "weekly", "subject"):
        period = "weekly"
    subject_id = request.query_params.get("subject")
    subject_id = int(subject_id) if subject_id and subject_id.isdigit() else None
    return Response(leaderboard(period, request.user, subject_id))


@api_view(["GET"])
def xp_history(request):
    rows = XPTransaction.objects.filter(user=request.user)[:30]
    return Response([{"amount": r.amount, "reason": r.reason, "created_at": r.created_at} for r in rows])
