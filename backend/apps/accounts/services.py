from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.audit import audit
from apps.gamification.models import Streak
from apps.referrals.services import bind_referral
from apps.wallet import services as wallet
from apps.wallet.models import CreditTransaction

from .models import SignupBonusClaim, StudentProfile, User


def create_student(email: str, *, referral_code: str = "", ip=None, request=None) -> User:
    with transaction.atomic():
        user = User.objects.create_user(email=email, email_verified_at=timezone.now())
        ensure_account_records(user)
        bind_referral(user, referral_code)
        grant_signup_bonus(user, ip=ip)
    audit("account.created", actor=user, target=user, request=request, referred=bool(referral_code))
    return user


def ensure_account_records(user: User) -> None:
    """Every account needs a profile, streak and wallet, however it was created
    (OTP sign-up, createsuperuser, Django admin, shell). Idempotent."""
    StudentProfile.objects.get_or_create(user=user)
    Streak.objects.get_or_create(user=user)
    wallet.get_wallet(user)


def grant_signup_bonus(user: User, ip=None) -> bool:
    """Exactly once per account AND once per canonical email, ever."""
    if user.signup_bonus_granted:
        return False
    try:
        with transaction.atomic():
            SignupBonusClaim.objects.create(canonical_email=user.canonical_email, user=user, ip_address=ip)
    except IntegrityError:
        return False
    wallet.credit(
        user, settings.SIGNUP_BONUS_CREDITS, CreditTransaction.Kind.SIGNUP_BONUS, f"signup_bonus:{user.pk}",
        "Welcome bonus — 100 free credits",
    )
    User.objects.filter(pk=user.pk).update(signup_bonus_granted=True)
    user.signup_bonus_granted = True
    return True
