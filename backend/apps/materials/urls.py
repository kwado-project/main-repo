from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("materials", views.MaterialViewSet, basename="material")
urlpatterns = router.urls
