from django.urls import path

from . import views

urlpatterns = [
    path("roadmaps/current/", views.current),
    path("roadmaps/generate/", views.generate),
    path("roadmaps/tasks/<int:task_id>/", views.update_task),
]
