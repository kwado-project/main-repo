from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("ai/conversations", views.ConversationViewSet, basename="ai-conversation")
urlpatterns = router.urls
