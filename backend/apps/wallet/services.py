"""Credit wallet engine.

Invariants
  * Every balance change is a row in the append-only CreditTransaction ledger.
  * Every change runs inside `transaction.atomic()` with the wallet row locked
    (`SELECT … FOR UPDATE`), so concurrent requests serialise per wallet and
    can never overspend.
  * Every change carries a unique idempotency key: replaying the same
    operation returns the original transaction instead of applying it twice.
  * Spendable balance never goes below zero (enforced in code and by a DB
    CHECK constraint).
"""
from contextlib import contextmanager
from dataclasses import dataclass

from django.core.cache import cache
from django.db import IntegrityError, transaction

from apps.core.exceptions import InsufficientCredits

from .models import ActivityPricing, CreditTransaction, Wallet

Kind = CreditTransaction.Kind

DEFAULT_PRICING = {
    "daily_practice": ("Daily practice quiz (10 questions)", 5),
    "topic_quiz": ("Topic quiz (20 questions)", 10),
    "subject_assessment": ("Subject assessment (40 questions)", 15),
    "mock_exam": ("Full mock examination", 25),
    "diagnostic": ("Diagnostic assessment", 20),
    "ai_tutor_response": ("AI tutor response", 2),
    "ai_practice_set": ("AI-generated practice set", 5),
    "ai_topic_explanation": ("AI topic explanation", 3),
    "ai_roadmap": ("AI roadmap generation", 15),
    "document_analysis": ("Uploaded document analysis", 10),
}

PRICING_CACHE_KEY = "activity_pricing:v1"


def get_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user)
    return wallet


def pricing_table() -> dict:
    data = cache.get(PRICING_CACHE_KEY)
    if data is None:
        data = {k: {"label": label, "credits": c} for k, (label, c) in DEFAULT_PRICING.items()}
        for row in ActivityPricing.objects.filter(is_active=True):
            data[row.key] = {"label": row.label, "credits": row.credits}
        cache.set(PRICING_CACHE_KEY, data, 300)
    return data


def invalidate_pricing_cache():
    cache.delete(PRICING_CACHE_KEY)


def price_of(activity_key: str) -> int:
    try:
        return int(pricing_table()[activity_key]["credits"])
    except KeyError:
        raise ValueError(f"Unknown activity {activity_key}")


def _apply(user, amount, kind, idempotency_key, description, **extra) -> CreditTransaction:
    existing = CreditTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    try:
        with transaction.atomic():
            get_wallet(user)
            wallet = Wallet.objects.select_for_update().get(user=user)
            # Re-check under the lock: a concurrent request may have just won.
            existing = CreditTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing
            new_balance = wallet.balance + amount
            if new_balance < 0:
                raise InsufficientCredits(
                    detail={"detail": "You do not have enough credits for this activity.",
                            "code": "insufficient_credits", "required": -amount, "balance": wallet.balance}
                )
            wallet.balance = new_balance
            if amount > 0:
                if kind == Kind.PURCHASE:
                    wallet.total_purchased += amount
                elif kind in (Kind.SIGNUP_BONUS, Kind.REFERRAL_REWARD, Kind.ADJUSTMENT):
                    wallet.total_earned += amount
                elif kind == Kind.REFUND:
                    wallet.total_spent = max(0, wallet.total_spent - amount)
            elif kind == Kind.SPEND:
                wallet.total_spent += -amount
            wallet.save(update_fields=["balance", "total_purchased", "total_earned", "total_spent", "updated_at"])
            return CreditTransaction.objects.create(
                wallet=wallet, kind=kind, amount=amount, balance_after=new_balance,
                idempotency_key=idempotency_key, description=description, **extra,
            )
    except IntegrityError:
        # Lost a race on the unique idempotency key — return the winner.
        return CreditTransaction.objects.get(idempotency_key=idempotency_key)


def credit(user, amount: int, kind: str, idempotency_key: str, description: str, **extra):
    assert amount > 0
    return _apply(user, amount, kind, idempotency_key, description, **extra)


def debit(user, amount: int, kind: str, idempotency_key: str, description: str, **extra):
    assert amount > 0
    return _apply(user, -amount, kind, idempotency_key, description, **extra)


def debit_up_to(user, amount: int, kind: str, idempotency_key: str, description: str, **extra):
    """Debit as much as possible without going negative (used for reversals)."""
    existing = CreditTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing, 0
    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(user=user)
        take = min(amount, wallet.balance)
        shortfall = amount - take
        if take == 0:
            # Still record a zero-value reversal for the audit trail.
            txn = CreditTransaction.objects.create(
                wallet=wallet, kind=kind, amount=0, balance_after=wallet.balance,
                idempotency_key=idempotency_key, description=description,
                metadata={**extra.pop("metadata", {}), "shortfall": shortfall}, **extra,
            )
            return txn, shortfall
        meta = {**extra.pop("metadata", {}), "requested": amount, "shortfall": shortfall}
        return _apply(user, -take, kind, idempotency_key, description, metadata=meta, **extra), shortfall


def refund(charge: CreditTransaction, reason: str) -> CreditTransaction:
    """Refund a SPEND transaction exactly once."""
    return credit(
        charge.wallet.user, -charge.amount, Kind.REFUND, f"refund:{charge.idempotency_key}",
        f"Refund — {reason}", activity_key=charge.activity_key, related=charge,
        reference_type=charge.reference_type, reference_id=charge.reference_id,
    )


@dataclass
class Charge:
    transaction: CreditTransaction | None
    credits: int
    refunded: bool = False


def charge_activity(user, activity_key: str, idempotency_key: str, *, reference_type="", reference_id="") -> Charge:
    cost = price_of(activity_key)
    if cost <= 0:
        return Charge(None, 0)
    label = pricing_table()[activity_key]["label"]
    txn = debit(user, cost, Kind.SPEND, f"spend:{idempotency_key}", label, activity_key=activity_key,
                reference_type=reference_type, reference_id=reference_id)
    return Charge(txn, cost)


@contextmanager
def paid_activity(user, activity_key: str, idempotency_key: str, **ref):
    """Hold credits for an activity; refund automatically if the block fails.

        with paid_activity(user, "ai_tutor_response", key) as charge:
            result = call_ai(...)   # any exception → full refund, re-raised
    """
    charge = charge_activity(user, activity_key, idempotency_key, **ref)
    try:
        yield charge
    except BaseException:
        if charge.transaction is not None:
            refund(charge.transaction, "activity did not complete")
            charge.refunded = True
        raise
