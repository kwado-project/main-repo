import pytest

pytestmark = pytest.mark.django_db

ENDPOINTS = ["overview", "examinations", "exam-subjects", "subjects", "topics", "questions", "questions/stats", "lessons",
             "learning-paths", "learning-path-nodes", "pricing", "packages", "ai-config", "settings", "transactions",
             "payments", "referral-rewards", "users", "materials", "audit-logs"]


def test_admin_endpoints_and_permissions(seeded, make_student, auth):
    admin = make_student("boss@example.com")
    admin.role = "admin"; admin.save()
    api = auth(admin)
    for e in ENDPOINTS:
        assert api.get(f"/api/admin-api/{e}/").status_code == 200, e
    cm = make_student("cm@example.com")
    cm.role = "content_manager"; cm.save()
    api2 = auth(cm)
    assert api2.get("/api/admin-api/questions/").status_code == 200
    assert api2.get("/api/admin-api/payments/").status_code == 403
    student = make_student("kid@example.com")
    assert auth(student).get("/api/admin-api/questions/").status_code == 403


def test_question_workflow_requires_verified_key_and_second_reviewer(seeded, make_student, auth):
    from apps.examinations.models import Subject, Topic
    cm = make_student("cm2@example.com"); cm.role = "content_manager"; cm.save()
    api = auth(cm)
    s = Subject.objects.get(name="Biology"); t = Topic.objects.filter(subject=s).first()
    q = api.post("/api/admin-api/questions/", {"subject": s.id, "topic": t.id, "text": "Which gas do plants absorb?",
                 "explanation": "Plants absorb CO2 for photosynthesis.", "difficulty": 1,
                 "options": [{"label": "A", "text": "Oxygen"}, {"label": "B", "text": "Carbon dioxide"}]}, format="json").data
    assert api.post(f"/api/admin-api/questions/{q['id']}/transition/", {"status": "published"}, format="json").status_code == 400
    api.post(f"/api/admin-api/questions/{q['id']}/transition/", {"status": "validated"}, format="json")
    opt = q["options"][1]["id"]
    api.post(f"/api/admin-api/questions/{q['id']}/transition/", {"status": "answer_verified", "correct_option": opt}, format="json")
    api.post(f"/api/admin-api/questions/{q['id']}/transition/", {"status": "in_review"}, format="json")
    r = api.post(f"/api/admin-api/questions/{q['id']}/transition/", {"status": "published"}, format="json")
    assert r.status_code == 400  # same person cannot verify and publish
    other = make_student("cm3@example.com"); other.role = "content_manager"; other.save()
    assert auth(other).post(f"/api/admin-api/questions/{q['id']}/transition/", {"status": "published"}, format="json").status_code == 200
