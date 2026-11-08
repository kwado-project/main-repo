import pytest


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield


@pytest.fixture
def seeded(db):
    from django.core.management import call_command
    call_command("seed", verbosity=0)


@pytest.fixture
def api():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def make_student(db):
    from apps.accounts.services import create_student

    def _make(email="ada@example.com", referral_code=""):
        return create_student(email, referral_code=referral_code)
    return _make


@pytest.fixture
def auth(api):
    def _auth(user):
        from rest_framework_simplejwt.tokens import RefreshToken
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return api
    return _auth
