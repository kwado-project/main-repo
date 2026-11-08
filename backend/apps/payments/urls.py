from django.urls import path

from . import views

urlpatterns = [
    path("payments/", views.PaymentList.as_view()),
    path("payments/initialize/", views.initialize),
    path("payments/verify/<str:reference>/", views.verify),
    path("payments/receipt/<str:reference>/", views.receipt),
    path("payments/sandbox/<str:reference>/complete/", views.sandbox_complete),
    path("payments/webhooks/paystack/", views.paystack_webhook),
]
