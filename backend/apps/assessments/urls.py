from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("assessments/attempts", views.AttemptViewSet, basename="attempt")

urlpatterns = router.urls + [
    path("assessments/progress/", views.progress),
    path("assessments/subjects/<int:subject_id>/topics/", views.topic_mastery),
]
