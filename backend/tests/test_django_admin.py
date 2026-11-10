import pytest
from django.contrib import admin
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_every_registered_model_admin_renders(seeded, client):
    from apps.accounts.models import User
    su = User.objects.create_superuser("root@example.com", password="pw-for-tests-only")
    client.force_login(su)
    labels = {m._meta.label for m in admin.site._registry}
    for required in ("examinations.Examination", "examinations.Subject", "examinations.Topic", "questions.Question",
                     "learning.Lesson", "payments.Payment", "wallet.CreditTransaction"):
        assert required in labels, required
    for model, model_admin in admin.site._registry.items():
        info = (model._meta.app_label, model._meta.model_name)
        assert client.get(reverse("admin:%s_%s_changelist" % info)).status_code == 200, info
        obj = model.objects.first()
        if obj is not None:
            assert client.get(reverse("admin:%s_%s_change" % info, args=[obj.pk])).status_code == 200, info
        if model_admin.has_add_permission(type("R", (), {"user": su})()):
            assert client.get(reverse("admin:%s_%s_add" % info)).status_code == 200, info


def test_payments_are_read_only_in_django_admin(seeded, client):
    from apps.accounts.models import User
    from apps.payments.models import Payment
    su = User.objects.create_superuser("root2@example.com", password="pw-for-tests-only")
    client.force_login(su)
    assert client.get(reverse("admin:payments_payment_add")).status_code == 403
    assert Payment._meta.label in {m._meta.label for m in admin.site._registry}
