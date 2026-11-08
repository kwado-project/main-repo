from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("learning/lessons", views.LessonViewSet, basename="lesson")

urlpatterns = router.urls + [
    path("learning/paths/<int:subject_id>/", views.learning_path),
    path("learning/continue/", views.continue_learning),
]
