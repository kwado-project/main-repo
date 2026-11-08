from django.urls import path

from . import views

urlpatterns = [
    path("auth/otp/request/", views.RequestOTPView.as_view()),
    path("auth/otp/verify/", views.VerifyOTPView.as_view()),
    path("auth/refresh/", views.RefreshView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
]
