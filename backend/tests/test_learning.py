import pytest

from apps.examinations.models import Examination, Subject
from apps.questions.models import AnswerKey

pytestmark = pytest.mark.django_db


def _setup(seeded, make_student, auth, email="learner@example.com"):
    u = make_student(email)
    api = auth(u)
    jamb = Examination.objects.get(code="jamb")
    ids = list(Subject.objects.filter(name__in=["English Language", "Mathematics", "Physics", "Chemistry"]).values_list("id", flat=True))
    r = api.post("/api/student-exams/", {"examination_id": jamb.id, "subject_ids": ids, "exam_date": "2030-05-01"}, format="json")
    assert r.status_code == 201, r.data
    return u, api, r.data["id"]


def test_subject_rules_enforced(seeded, make_student, auth):
    u = make_student()
    jamb = Examination.objects.get(code="jamb")
    ids = list(Subject.objects.filter(name__in=["Mathematics", "Physics", "Chemistry", "Biology"]).values_list("id", flat=True))
    r = auth(u).post("/api/student-exams/", {"examination_id": jamb.id, "subject_ids": ids}, format="json")
    assert r.status_code == 400 and "compulsory" in str(r.data)


def test_quiz_charges_scores_on_server_and_awards_xp(seeded, make_student, auth):
    u, api, se = _setup(seeded, make_student, auth)
    maths = Subject.objects.get(name="Mathematics")
    r = api.post("/api/assessments/attempts/", {"kind": "daily", "subject": maths.id, "student_exam": se}, format="json")
    assert r.status_code == 201, r.data
    attempt = r.data
    assert attempt["credits_charged"] == 5
    assert all("correct_option" not in q for q in attempt["questions"])  # no answers leaked
    for i, q in enumerate(attempt["questions"]):
        key = AnswerKey.objects.get(question_id=q["id"]).correct_option_id
        choice = key if i % 2 == 0 else next(o["id"] for o in q["options"] if o["id"] != key)
        res = api.post(f"/api/assessments/attempts/{attempt['id']}/answer/", {"question": q["id"], "option": choice}, format="json")
        assert res.data["question"]["is_correct"] == (i % 2 == 0)  # practice → instant feedback
    res = api.post(f"/api/assessments/attempts/{attempt['id']}/submit/")
    expected = (len(attempt["questions"]) + 1) // 2
    assert res.data["correct_count"] == expected
    assert res.data["xp_earned"] > 0
    u.wallet.refresh_from_db(); u.profile.refresh_from_db()
    assert u.wallet.balance == 95 and u.profile.total_xp >= res.data["xp_earned"]


def test_exam_mode_hides_corrections_until_submit(seeded, make_student, auth):
    u, api, se = _setup(seeded, make_student, auth, "mock@example.com")
    r = api.post("/api/assessments/attempts/", {"kind": "diagnostic", "student_exam": se}, format="json")
    assert r.status_code == 201, r.data
    q = r.data["questions"][0]
    res = api.post(f"/api/assessments/attempts/{r.data['id']}/answer/", {"question": q["id"], "option": q["options"][0]["id"]}, format="json")
    assert "is_correct" not in res.data["question"]
    done = api.post(f"/api/assessments/attempts/{r.data['id']}/submit/").data
    assert "correct_option" in done["questions"][0]


def test_students_cannot_see_each_others_attempts(seeded, make_student, auth):
    u, api, se = _setup(seeded, make_student, auth, "owner@example.com")
    maths = Subject.objects.get(name="Mathematics")
    a = api.post("/api/assessments/attempts/", {"kind": "daily", "subject": maths.id}, format="json").data
    other = make_student("intruder@example.com")
    api2 = auth(other)
    assert api2.get(f"/api/assessments/attempts/{a['id']}/").status_code == 404
    assert api2.post(f"/api/assessments/attempts/{a['id']}/submit/").status_code == 404


def test_insufficient_credits_blocks_without_partial_charge(seeded, make_student, auth):
    from apps.wallet import services as wallet
    u, api, se = _setup(seeded, make_student, auth, "broke@example.com")
    wallet.debit(u, 98, "spend", "drain", "drain")
    r = api.post("/api/assessments/attempts/", {"kind": "mock", "student_exam": se}, format="json")
    assert r.status_code == 402
    u.wallet.refresh_from_db()
    assert u.wallet.balance == 2


def test_roadmap_and_ai_tutor_refund(seeded, make_student, auth):
    u, api, se = _setup(seeded, make_student, auth, "rm@example.com")
    assert api.post("/api/roadmaps/generate/", {"student_exam": se}, format="json").status_code == 201
    rm = api.get("/api/roadmaps/current/").data
    assert rm["tasks"] and rm["roadmap"]["summary"]
    conv = api.post("/api/ai/conversations/", {}, format="json").data
    before = u.wallet.balance if False else api.get("/api/wallet/").data["balance"]
    resp = api.post(f"/api/ai/conversations/{conv['id']}/messages/", {"content": "FAIL_AI please"}, format="json")
    body = b"".join(resp.streaming_content).decode()
    assert "event: error" in body
    assert api.get("/api/wallet/").data["balance"] == before
    resp = api.post(f"/api/ai/conversations/{conv['id']}/messages/", {"content": "Explain osmosis"}, format="json")
    body = b"".join(resp.streaming_content).decode()
    assert "event: done" in body
    assert api.get("/api/wallet/").data["balance"] == before - 2
