import pytest

from apps.accounts.models import StudentProfile, User
from apps.gamification.models import Streak
from apps.wallet.models import Wallet

pytestmark = pytest.mark.django_db


def test_superuser_gets_profile_and_me_works(auth):
    u = User.objects.create_superuser(email="kwado@example.com", password="x-strong-pass-123")
    assert StudentProfile.objects.filter(user=u).exists() and Streak.objects.filter(user=u).exists()
    assert Wallet.objects.filter(user=u).exists()
    r = auth(u).get("/api/me/")
    assert r.status_code == 200 and r.data["profile"]["total_xp"] == 0
