from django.conf import settings
from django.db.models import Sum
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Referral, ReferralReward


def _mask(email):
    local, _, domain = email.partition("@")
    return f"{local[:2]}{'•' * max(2, len(local) - 2)}@{domain}"


@api_view(["GET"])
def dashboard(request):
    user = request.user
    refs = Referral.objects.filter(referrer=user).select_related("referred")
    rewards = ReferralReward.objects.filter(referral__referrer=user).select_related("referral__referred")
    active_ids = set(rewards.filter(status="granted").values_list("referral_id", flat=True))
    link = f"{settings.FRONTEND_URL}/register?ref={user.referral_code}"
    return Response({
        "code": user.referral_code, "link": link,
        "share_text": f"I'm preparing for my exams on Kwado AI — learn, play, practise, pass! "
                      f"Sign up with my link and get 100 free credits: {link}",
        "reward_percent": settings.REFERRAL_REWARD_PERCENT,
        "total_referrals": refs.count(), "active_referrals": len(active_ids),
        "total_earned": rewards.filter(status="granted").aggregate(s=Sum("reward_credits"))["s"] or 0,
        "referrals": [{"name": r.referred.first_name, "email": _mask(r.referred.email), "joined_at": r.created_at,
                       "active": r.id in active_ids} for r in refs[:50]],
        "activity": [{"friend": rw.referral.referred.first_name, "purchased": rw.purchased_credits,
                      "reward": rw.reward_credits, "status": rw.status, "date": rw.created_at} for rw in rewards[:50]],
    })
