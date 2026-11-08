"""Passwordless email OTP.

* 6-digit codes from `secrets`, stored only as HMAC-SHA256 (keyed with the
  server secret) — a DB leak does not reveal codes.
* 5-minute expiry, single use, max 5 verification attempts per code.
* 60-second resend cooldown per email; per-IP/email throttles at the API layer.
* Responses never reveal whether an email is registered.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import EmailOTP, normalize_email


def _hash(email: str, code: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def cooldown_remaining(email: str) -> int:
    last = EmailOTP.objects.filter(email=email).order_by("-created_at").values_list("created_at", flat=True).first()
    if not last:
        return 0
    elapsed = (timezone.now() - last).total_seconds()
    return max(0, int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed))


def issue(email: str, purpose: str, *, referral_code: str = "", ip=None) -> str:
    email = normalize_email(email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    with transaction.atomic():
        EmailOTP.objects.filter(email=email, consumed_at__isnull=True, invalidated=False).update(invalidated=True)
        EmailOTP.objects.create(
            email=email, purpose=purpose, code_hash=_hash(email, code),
            expires_at=timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS),
            referral_code=(referral_code or "")[:12].upper(), ip_address=ip,
        )
    return code


class OTPError(Exception):
    def __init__(self, message, code="invalid_code"):
        super().__init__(message)
        self.message = message
        self.code = code


def verify(email: str, code: str) -> EmailOTP:
    email = normalize_email(email)
    code = (code or "").strip()
    error = None
    # The atomic block must COMMIT the attempt counter even when the code is
    # wrong, so errors are raised only after it exits.
    with transaction.atomic():
        otp = (
            EmailOTP.objects.select_for_update()
            .filter(email=email, consumed_at__isnull=True, invalidated=False)
            .order_by("-created_at")
            .first()
        )
        if not otp or otp.expires_at <= timezone.now():
            error = OTPError("This code has expired. Request a new one.", "code_expired")
        elif otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            otp.invalidated = True
            otp.save(update_fields=["invalidated"])
            error = OTPError("Too many attempts. Request a new code.", "too_many_attempts")
        else:
            otp.attempts += 1
            if len(code) == 6 and code.isdigit() and hmac.compare_digest(otp.code_hash, _hash(email, code)):
                otp.consumed_at = timezone.now()
                otp.save(update_fields=["attempts", "consumed_at"])
            else:
                if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
                    otp.invalidated = True
                otp.save(update_fields=["attempts", "invalidated"])
                left = max(0, settings.OTP_MAX_ATTEMPTS - otp.attempts)
                error = OTPError(f"That code is not correct. {left} attempt{'s' if left != 1 else ''} left.")
    if error:
        raise error
    return otp
