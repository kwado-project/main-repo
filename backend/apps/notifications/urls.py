from django.urls import path

from . import views

urlpatterns = [path("notifications/", views.list_notifications), path("notifications/read/", views.mark_read)]
