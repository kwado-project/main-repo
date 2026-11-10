from django.conf import settings
from rest_framework import generics, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.pagination import LedgerCursorPagination

from .models import CreditPackage, CreditTransaction
from .services import get_wallet, pricing_table


class PackageSerializer(serializers.ModelSerializer):
    price_naira = serializers.IntegerField(read_only=True)

    class Meta:
        model = CreditPackage
        fields = ("id", "name", "slug", "credits", "price_naira", "bonus_label", "is_featured")


class TransactionSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display")

    class Meta:
        model = CreditTransaction
        fields = ("id", "kind", "kind_label", "amount", "balance_after", "description", "activity_key",
                  "reference_type", "reference_id", "created_at")


@api_view(["GET"])
def wallet_summary(request):
    w = get_wallet(request.user)
    return Response({"balance": w.balance, "total_purchased": w.total_purchased, "total_earned": w.total_earned,
                     "total_spent": w.total_spent, "naira_per_credit": settings.NAIRA_PER_CREDIT,
                     "custom_min": settings.CUSTOM_CREDITS_MIN, "custom_max": settings.CUSTOM_CREDITS_MAX})


class TransactionList(generics.ListAPIView):
    serializer_class = TransactionSerializer
    pagination_class = LedgerCursorPagination

    def get_queryset(self):
        qs = CreditTransaction.objects.filter(wallet__user=self.request.user)
        if k := self.request.query_params.get("kind"):
            qs = qs.filter(kind=k)
        return qs


@api_view(["GET"])
@permission_classes([AllowAny])
def packages(request):
    return Response(PackageSerializer(CreditPackage.objects.filter(is_active=True), many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def pricing(request):
    return Response([{"key": k, **v} for k, v in pricing_table().items()])
