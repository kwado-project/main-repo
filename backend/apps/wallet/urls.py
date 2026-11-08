from django.urls import path

from . import views

urlpatterns = [
    path("wallet/", views.wallet_summary),
    path("wallet/transactions/", views.TransactionList.as_view()),
    path("wallet/packages/", views.packages),
    path("wallet/pricing/", views.pricing),
]
