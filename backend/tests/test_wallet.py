import threading

import pytest
from django.db import connection

from apps.core.exceptions import InsufficientCredits
from apps.wallet import services as wallet
from apps.wallet.models import CreditTransaction


@pytest.mark.django_db
def test_idempotent_debit_and_refund(make_student):
    u = make_student()
    t1 = wallet.debit(u, 10, "spend", "k1", "x")
    t2 = wallet.debit(u, 10, "spend", "k1", "x")
    assert t1.pk == t2.pk
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 90
    wallet.refund(t1, "test")
    wallet.refund(t1, "test")
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 100


@pytest.mark.django_db
def test_never_negative(make_student):
    u = make_student()
    with pytest.raises(InsufficientCredits):
        wallet.debit(u, 101, "spend", "big", "x")
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 100


@pytest.mark.django_db
def test_paid_activity_refunds_on_failure(make_student):
    u = make_student()
    with pytest.raises(RuntimeError):
        with wallet.paid_activity(u, "ai_tutor_response", "act-1"):
            raise RuntimeError("AI down")
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 100
    kinds = list(CreditTransaction.objects.filter(wallet__user=u).values_list("kind", flat=True))
    assert "refund" in kinds


@pytest.mark.django_db(transaction=True)
def test_concurrent_spending_cannot_overspend(make_student):
    u = make_student("race@example.com")  # 100 credits
    errors, ok = [], []

    def spend(i):
        try:
            wallet.debit(u, 30, "spend", f"race-{i}", "x")
            ok.append(i)
        except InsufficientCredits:
            errors.append(i)
        finally:
            connection.close()

    threads = [threading.Thread(target=spend, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    u.wallet.refresh_from_db()
    assert len(ok) == 3 and u.wallet.balance == 10
