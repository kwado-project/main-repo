from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.examinations import views as exam_views


def health(request):
    with connection.cursor() as c:
        c.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


router = SimpleRouter()
router.register("examinations", exam_views.ExaminationViewSet, basename="examination")
router.register("subjects", exam_views.SubjectViewSet, basename="subject")
router.register("student-exams", exam_views.StudentExamViewSet, basename="student-exam")

api = [
    *router.urls,
    path("", include("apps.accounts.urls")),
    path("", include("apps.assessments.urls")),
    path("", include("apps.learning.urls")),
    path("", include("apps.gamification.urls")),
    path("", include("apps.wallet.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.referrals.urls")),
    path("", include("apps.ai_tutor.urls")),
    path("", include("apps.roadmaps.urls")),
    path("", include("apps.materials.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.analytics.urls")),
    path("", include("apps.research.urls")),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/health/", health),
    path("api/", include(api)),
]
