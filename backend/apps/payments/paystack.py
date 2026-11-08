"""Thin Paystack REST client (server-side only; secret key never leaves the backend)."""
import hashlib
import hmac

import requests
from django.conf import settings


class PaystackError(Exception):
    pass


def _headers():
    return {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}


def initialize(*, email: str, amount_kobo: int, reference: str, callback_url: str, metadata: dict) -> dict:
    r = requests.post(
        f"{settings.PAYSTACK_BASE_URL}/transaction/initialize",
        json={"email": email, "amount": amount_kobo, "reference": reference, "currency": "NGN",
              "callback_url": callback_url, "metadata": metadata},
        headers=_headers(), timeout=20,
    )
    body = r.json() if r.content else {}
    if r.status_code >= 400 or not body.get("status"):
        raise PaystackError(body.get("message") or f"HTTP {r.status_code}")
    return body["data"]


def verify(reference: str) -> dict:
    r = requests.get(f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}", headers=_headers(), timeout=20)
    body = r.json() if r.content else {}
    if r.status_code >= 400 or not body.get("status"):
        raise PaystackError(body.get("message") or f"HTTP {r.status_code}")
    return body["data"]


def valid_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature or not settings.PAYSTACK_SECRET_KEY:
        return False
    expected = hmac.new(settings.PAYSTACK_SECRET_KEY.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)
