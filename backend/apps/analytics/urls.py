from django.urls import path
from rest_framework.routers import SimpleRouter

from . import admin_api as a

r = SimpleRouter()
for prefix, vs in [
    ("examinations", a.ExaminationVS), ("exam-subjects", a.ExamSubjectVS), ("subjects", a.SubjectVS),
    ("topics", a.TopicVS), ("questions", a.QuestionVS), ("lessons", a.LessonVS),
    ("learning-paths", a.LearningPathVS), ("learning-path-nodes", a.LearningPathNodeVS),
    ("pricing", a.PricingVS), ("packages", a.PackageVS), ("ai-config", a.AIConfigVS), ("settings", a.SettingVS),
    ("transactions", a.TransactionVS), ("payments", a.PaymentVS), ("referral-rewards", a.RewardVS),
    ("users", a.UserVS), ("materials", a.MaterialAdminVS), ("audit-logs", a.AuditVS),
]:
    r.register(f"admin-api/{prefix}", vs, basename=f"admin-{prefix}")

urlpatterns = r.urls + [
    path("admin-api/overview/", a.overview),
    path("admin-api/broadcast/", a.broadcast),
]
