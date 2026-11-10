"""Payment lifecycle. Credits are awarded ONLY after server-side verification
of reference, amount, currency and status with the provider."""
import logging
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit import audit
from apps.notifications.models import notify
from apps.referrals.services import grant_referral_reward, reverse_referral_reward
from apps.wallet import services as wallet
from apps.wallet.models import CreditTransaction

from . import paystack
from .models import Payment

logger = logging.getLogger("kwado.payments")


class PaymentVerificationError(Exception):
    pass


def new_reference() -> str:
    return f"KWD-{timezone.now():%y%m%d}-{secrets.token_hex(8).upper()}"


def custom_price_kobo(credits: int) -> int:
    return credits * settings.NAIRA_PER_CREDIT * 100


def initialize_payment(user, package=None, request=None, *, credits: int | None = None) -> Payment:
    """Start a purchase of a package, or of a custom number of credits.

    The price is always computed here on the server, never taken from the client.
    """
    if package is not None:
        amount_kobo, credits = package.price_kobo, package.credits
    else:
        if credits is None or not (settings.CUSTOM_CREDITS_MIN <= credits <= settings.CUSTOM_CREDITS_MAX):
            raise ValueError("invalid credit amount")
        amount_kobo = custom_price_kobo(credits)
    payment = Payment.objects.create(
        user=user, package=package, reference=new_reference(), amount_kobo=amount_kobo,
        credits=credits,
        provider=Payment.Provider.DEV_SANDBOX if settings.PAYMENTS_DEV_SANDBOX else Payment.Provider.PAYSTACK,
    )
    callback = f"{settings.FRONTEND_URL}/app/wallet/payment/callback"
    if payment.provider == Payment.Provider.DEV_SANDBOX:
        payment.authorization_url = f"{settings.FRONTEND_URL}/app/wallet/payment/sandbox?reference={payment.reference}"
    else:
        data = paystack.initialize(
            email=user.email, amount_kobo=payment.amount_kobo, reference=payment.reference,
            callback_url=callback,
            metadata={"user_id": user.id, "package": package.slug if package else "custom", "credits": credits},
        )
        payment.authorization_url = data["authorization_url"]
    payment.save(update_fields=["authorization_url"])
    audit("payment.initialized", actor=user, target=payment, request=request,
          package=package.slug if package else "custom", credits=credits)
    return payment


def _check(payment: Payment, data: dict):
    if data.get("reference") != payment.reference:
        raise PaymentVerificationError("reference mismatch")
    if int(data.get("amount", -1)) != payment.amount_kobo:
        raise PaymentVerificationError("amount mismatch")
    if (data.get("currency") or "NGN").upper() != payment.currency:
        raise PaymentVerificationError("currency mismatch")


def verify_payment(payment: Payment) -> Payment:
    """Ask the provider for the truth and fulfil if it succeeded."""
    if payment.status != Payment.Status.PENDING:
        return payment
    if payment.provider == Payment.Provider.DEV_SANDBOX:
        return payment  # completed only via the explicit sandbox action
    data = paystack.verify(payment.reference)
    status = data.get("status")
    if status == "success":
        _check(payment, data)
        return fulfil_payment(payment, data)
    if status in ("failed", "abandoned", "reversed"):
        Payment.objects.filter(pk=payment.pk, status=Payment.Status.PENDING).update(
            status=Payment.Status.FAILED if status != "abandoned" else Payment.Status.ABANDONED,
            gateway_response=(data.get("gateway_response") or "")[:255], raw_verification=data,
        )
        payment.refresh_from_db()
    return payment


def fulfil_payment(payment: Payment, data: dict) -> Payment:
    """Idempotently mark a verified payment successful and award credits."""
    with transaction.atomic():
        p = Payment.objects.select_for_update().get(pk=payment.pk)
        if p.status == Payment.Status.SUCCESS:
            return p
        if p.status not in (Payment.Status.PENDING, Payment.Status.FAILED, Payment.Status.ABANDONED):
            return p
        txn = wallet.credit(
            p.user, p.credits, CreditTransaction.Kind.PURCHASE, f"payment:{p.reference}",
            f"Purchased {p.credits} credits ({p.label})",
            reference_type="payment", reference_id=p.reference,
        )
        p.status = Payment.Status.SUCCESS
        p.credit_transaction = txn
        p.verified_at = timezone.now()
        p.paid_at = data.get("paid_at") or timezone.now()
        p.channel = (data.get("channel") or "")[:30]
        p.gateway_response = (data.get("gateway_response") or "Successful")[:255]
        p.raw_verification = data
        p.save()
        grant_referral_reward(p)
    notify(p.user, "payment", "Payment confirmed",
           f"{p.credits} credits have been added to your wallet.", f"/app/wallet/receipt/{p.reference}")
    audit("payment.fulfilled", actor=p.user, target=p, credits=p.credits)
    return p


def refund_payment(payment: Payment, reason: str = "refund") -> Payment:
    """Handle a refund/chargeback: claw back purchased credits and referral reward."""
    with transaction.atomic():
        p = Payment.objects.select_for_update().get(pk=payment.pk)
        if p.status != Payment.Status.SUCCESS:
            return p
        txn, shortfall = wallet.debit_up_to(
            p.user, p.credits, CreditTransaction.Kind.REVERSAL, f"payment-reversal:{p.reference}",
            f"Reversal — payment {reason}", reference_type="payment", reference_id=p.reference,
        )
        p.status = Payment.Status.REFUNDED
        p.refunded_at = timezone.now()
        p.save(update_fields=["status", "refunded_at", "updated_at"])
        reverse_referral_reward(p)
    audit("payment.refunded", target=p, reason=reason, shortfall=shortfall)
    if shortfall:
        logger.warning("Refund shortfall of %s credits on %s", shortfall, p.reference)
    return p
