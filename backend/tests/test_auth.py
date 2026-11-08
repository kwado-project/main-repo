import pytest

from apps.accounts.models import EmailOTP, User
from apps.wallet.models import CreditTransaction

pytestmark = pytest.mark.django_db


def _request(api, email, intent="register", **extra):
    return api.post("/api/auth/otp/request/", {"email": email, "intent": intent, **extra}, format="json")


def test_register_flow_grants_exactly_100_credits_once(api):
    r = _request(api, "Tolu@Example.com")
    assert r.status_code == 200
    code = r.data["dev_code"]
    r = api.post("/api/auth/otp/verify/", {"email": "tolu@example.com", "code": code}, format="json")
    assert r.status_code == 200 and r.data["is_new"] is True
    assert "access" in r.data and "kwado_refresh" in r.cookies
    user = User.objects.get(email="tolu@example.com")
    assert user.wallet.balance == 100
    assert CreditTransaction.objects.filter(wallet__user=user, kind="signup_bonus").count() == 1
    # Code is single-use
    r = api.post("/api/auth/otp/verify/", {"email": "tolu@example.com", "code": code}, format="json")
    assert r.status_code == 400


def test_login_does_not_grant_bonus_again(api, make_student):
    u = make_student("bola@example.com")
    EmailOTP.objects.all().delete()
    code = _request(api, "bola@example.com", "login").data["dev_code"]
    r = api.post("/api/auth/otp/verify/", {"email": "bola@example.com", "code": code}, format="json")
    assert r.status_code == 200 and r.data["is_new"] is False
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 100


def test_gmail_alias_cannot_farm_bonus(make_student):
    a = make_student("chi.di@gmail.com")
    b = make_student("chidi+2@gmail.com")
    a.wallet.refresh_from_db(); b.wallet.refresh_from_db()
    assert a.wallet.balance == 100
    assert b.wallet.balance == 0


def test_generic_response_for_unknown_login_email(api):
    r = _request(api, "nobody@example.com", "login")
    assert r.status_code == 200 and "dev_code" not in r.data
    known = _request(api, "x@example.com", "register")
    assert r.data["detail"] == known.data["detail"]


def test_otp_expiry_attempts_and_cooldown(api):
    _request(api, "ife@example.com")
    assert _request(api, "ife@example.com").status_code == 429  # resend cooldown
    for _ in range(5):
        r = api.post("/api/auth/otp/verify/", {"email": "ife@example.com", "code": "000000"}, format="json")
    assert r.status_code == 400
    otp = EmailOTP.objects.get(email="ife@example.com")
    assert otp.invalidated and otp.code_hash and len(otp.code_hash) == 64  # stored hashed, never plain


def test_refresh_rotation_and_logout(api):
    code = _request(api, "kemi@example.com").data["dev_code"]
    api.post("/api/auth/otp/verify/", {"email": "kemi@example.com", "code": code}, format="json")
    r = api.post("/api/auth/refresh/")
    assert r.status_code == 200 and r.data["access"]
    old_cookie = r.cookies["kwado_refresh"].value
    api.post("/api/auth/logout/")
    api.cookies["kwado_refresh"] = old_cookie
    assert api.post("/api/auth/refresh/").status_code == 401
