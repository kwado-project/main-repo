import hashlib
import hmac
import json
from unittest import mock

import pytest
from django.test import override_settings

from apps.payments import services
from apps.payments.models import Payment
from apps.wallet.models import CreditPackage

pytestmark = pytest.mark.django_db


def _paystack_ok(p):
    return {"status": "success", "reference": p.reference, "amount": p.amount_kobo, "currency": "NGN",
            "channel": "card", "gateway_response": "Approved"}


@override_settings(PAYMENTS_DEV_SANDBOX=False, PAYSTACK_SECRET_KEY="sk_test_x")
def test_purchase_verify_and_referral_reward(seeded, make_student, auth):
    referrer = make_student("ref@example.com")
    buyer = make_student("buyer@example.com", referral_code=referrer.referral_code)
    pkg = CreditPackage.objects.get(slug="standard")  # 500 credits
    api = auth(buyer)
    with mock.patch("apps.payments.paystack.initialize", return_value={"authorization_url": "https://checkout.paystack.com/x"}):
        r = api.post("/api/payments/initialize/", {"package": pkg.id}, format="json")
    assert r.status_code == 201
    ref = r.data["reference"]
    buyer.wallet.refresh_from_db()
    assert buyer.wallet.balance == 100  # nothing awarded on initialise / redirect
    p = Payment.objects.get(reference=ref)
    with mock.patch("apps.payments.paystack.verify", return_value=_paystack_ok(p)):
        assert api.get(f"/api/payments/verify/{ref}/").data["status"] == "success"
        api.get(f"/api/payments/verify/{ref}/")  # replay is harmless
    buyer.wallet.refresh_from_db(); referrer.wallet.refresh_from_db()
    assert buyer.wallet.balance == 600
    assert referrer.wallet.balance == 100 + 100  # 20% of 500


@override_settings(PAYMENTS_DEV_SANDBOX=False, PAYSTACK_SECRET_KEY="sk_test_x")
def test_amount_mismatch_is_rejected(seeded, make_student, auth):
    u = make_student()
    pkg = CreditPackage.objects.get(slug="starter")
    p = Payment.objects.create(user=u, package=pkg, reference="KWD-TEST-1", amount_kobo=pkg.price_kobo, credits=pkg.credits)
    bad = {**_paystack_ok(p), "amount": 100}
    with mock.patch("apps.payments.paystack.verify", return_value=bad):
        r = auth(u).get("/api/payments/verify/KWD-TEST-1/")
    assert r.status_code == 409
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 100


@override_settings(PAYSTACK_SECRET_KEY="sk_test_x")
def test_webhook_signature_and_refund_reverses_reward(seeded, make_student, api):
    referrer = make_student("r2@example.com")
    buyer = make_student("b2@example.com", referral_code=referrer.referral_code)
    pkg = CreditPackage.objects.get(slug="basic")  # 250 → reward 50
    p = Payment.objects.create(user=buyer, package=pkg, reference="KWD-WH-1", amount_kobo=pkg.price_kobo, credits=250)
    body = json.dumps({"event": "charge.success", "data": {"id": 1, "reference": p.reference}}).encode()
    assert api.post("/api/payments/webhooks/paystack/", body, content_type="application/json",
                    HTTP_X_PAYSTACK_SIGNATURE="bad").status_code == 401
    sig = hmac.new(b"sk_test_x", body, hashlib.sha512).hexdigest()
    with mock.patch("apps.payments.paystack.verify", return_value=_paystack_ok(p)):
        r = api.post("/api/payments/webhooks/paystack/", body, content_type="application/json", HTTP_X_PAYSTACK_SIGNATURE=sig)
    assert r.status_code == 200
    referrer.wallet.refresh_from_db()
    assert referrer.wallet.balance == 150
    services.refund_payment(Payment.objects.get(pk=p.pk))
    referrer.wallet.refresh_from_db(); buyer.wallet.refresh_from_db()
    assert referrer.wallet.balance == 100 and buyer.wallet.balance == 100


def test_self_referral_ignored(make_student):
    from apps.referrals.services import bind_referral
    u = make_student("self@example.com")
    assert bind_referral(u, u.referral_code) is None


@override_settings(PAYMENTS_DEV_SANDBOX=False, PAYSTACK_SECRET_KEY="sk_test_x")
def test_custom_amount_purchase_priced_on_server_with_referral(seeded, make_student, auth):
    referrer = make_student("cref@example.com")
    buyer = make_student("cbuy@example.com", referral_code=referrer.referral_code)
    api = auth(buyer)
    with mock.patch("apps.payments.paystack.initialize", return_value={"authorization_url": "https://checkout.paystack.com/y"}) as init:
        r = api.post("/api/payments/initialize/", {"credits": 730, "amount": 1}, format="json")  # client "amount" is ignored
    assert r.status_code == 201, r.data
    assert r.data["credits"] == 730 and r.data["amount_naira"] == 7300 and r.data["package_name"] == "Custom amount"
    assert init.call_args.kwargs["amount_kobo"] == 730_000
    p = Payment.objects.get(reference=r.data["reference"])
    with mock.patch("apps.payments.paystack.verify", return_value=_paystack_ok(p)):
        assert api.get(f"/api/payments/verify/{p.reference}/").data["status"] == "success"
    buyer.wallet.refresh_from_db(); referrer.wallet.refresh_from_db()
    assert buyer.wallet.balance == 100 + 730
    assert referrer.wallet.balance == 100 + 146  # 20% of 730
    receipt = api.get(f"/api/payments/receipt/{p.reference}/").data
    assert receipt["package_name"] == "Custom amount" and receipt["credits"] == 730


@pytest.mark.parametrize("credits", [0, 49, 100001, -5, "abc", "12.5", None])
def test_custom_amount_validation(seeded, make_student, auth, credits):
    api = auth(make_student("cval@example.com"))
    r = api.post("/api/payments/initialize/", {"credits": credits}, format="json")
    assert r.status_code == 400 and r.data["code"] == "invalid_credits"
    assert not Payment.objects.exists()


def test_wallet_reports_custom_limits(make_student, auth):
    d = auth(make_student("lim@example.com")).get("/api/wallet/").data
    assert (d["custom_min"], d["custom_max"], d["naira_per_credit"]) == (50, 100000, 10)
