from django.urls import path

from . import views

urlpatterns = [path("referrals/", views.dashboard)]
