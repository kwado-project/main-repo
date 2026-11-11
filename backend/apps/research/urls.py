from django.urls import path
from rest_framework.routers import SimpleRouter

from . import api

r = SimpleRouter()
r.register("admin-api/research/sources", api.SourceViewSet, basename="research-source")
r.register("admin-api/research/documents", api.DocumentViewSet, basename="research-document")
r.register("admin-api/research/questions", api.QuestionViewSet, basename="research-question")

urlpatterns = r.urls + [
    path("admin-api/research/overview/", api.overview),
    path("admin-api/research/jobs/", api.job_list),
    path("admin-api/research/run/", api.run),
    path("admin-api/research/seeds/", api.add_seed),
]
