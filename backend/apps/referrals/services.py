from django.conf import settings

from apps.accounts.models import User
from apps.notifications.models import notify
from apps.wallet import services as wallet
from apps.wallet.models import CreditTransaction

from .models import Referral, ReferralReward


def bind_referral(new_user: User, code: str) -> Referral | None:
    """Bind at registration. Silently ignores invalid or self referrals."""
    code = (code or "").strip().upper()
    if not code:
        return None
    referrer = User.objects.filter(referral_code=code, is_active=True).first()
    if not referrer or referrer.pk == new_user.pk or referrer.canonical_email == new_user.canonical_email:
        return None
    if Referral.objects.filter(referred=new_user).exists():
        return None
    return Referral.objects.create(referrer=referrer, referred=new_user, code_used=code)


def reward_for(purchased_credits: int) -> int:
    return purchased_credits * settings.REFERRAL_REWARD_PERCENT // 100


def grant_referral_reward(payment):
    """Called inside the payment-fulfilment transaction. Purchases only —
    signup bonuses and other promotional credits never generate rewards."""
    referral = Referral.objects.filter(referred=payment.user).select_related("referrer").first()
    if not referral or not referral.referrer.is_active:
        return None
    if ReferralReward.objects.filter(payment=payment).exists():
        return None
    amount = reward_for(payment.credits)
    if amount <= 0:
        return None
    txn = wallet.credit(
        referral.referrer, amount, CreditTransaction.Kind.REFERRAL_REWARD, f"referral:{payment.reference}",
        f"Referral reward — a friend bought {payment.credits} credits",
        reference_type="referral_reward", reference_id=payment.reference,
    )
    reward = ReferralReward.objects.create(
        referral=referral, payment=payment, purchased_credits=payment.credits, reward_credits=amount, transaction=txn
    )
    notify(referral.referrer, "referral", f"You earned {amount} referral credits",
           "A friend you invited just bought credits.", "/app/referrals")
    return reward


def reverse_referral_reward(payment):
    reward = ReferralReward.objects.select_for_update().filter(payment=payment).first()
    if not reward or reward.status == ReferralReward.Status.REVERSED:
        return None
    txn, _ = wallet.debit_up_to(
        reward.referral.referrer, reward.reward_credits, CreditTransaction.Kind.REVERSAL,
        f"referral-reversal:{payment.reference}", "Referral reward reversed — purchase refunded",
        reference_type="referral_reward", reference_id=payment.reference,
    )
    reward.status = ReferralReward.Status.REVERSED
    reward.reversal_transaction = txn
    reward.save(update_fields=["status", "reversal_transaction", "updated_at"])
    return reward
