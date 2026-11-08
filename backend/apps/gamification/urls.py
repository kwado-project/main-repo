from django.urls import path

from . import views

urlpatterns = [
    path("gamification/summary/", views.summary),
    path("gamification/missions/", views.missions),
    path("gamification/badges/", views.badges),
    path("gamification/badges/seen/", views.badges_seen),
    path("gamification/leaderboard/", views.leaderboard_view),
    path("gamification/xp-history/", views.xp_history),
]
