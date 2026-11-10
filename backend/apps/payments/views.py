import json
import logging

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, serializers
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from apps.core.throttling import FlexUserThrottle as UserRateThrottle

from apps.wallet.models import CreditPackage

from . import paystack, services
from .models import Payment, WebhookEvent

logger = logging.getLogger("kwado.payments")


class PaymentThrottle(UserRateThrottle):
    scope = "payments"


class PaymentSerializer(serializers.ModelSerializer):
    package_name = serializers.CharField(source="label")
    amount_naira = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ("reference", "package_name", "credits", "amount_naira", "currency", "status", "provider", "channel",
                  "gateway_response", "created_at", "paid_at", "verified_at", "authorization_url")

    def get_amount_naira(self, obj):
        return obj.amount_kobo // 100


@api_view(["POST"])
@throttle_classes([PaymentThrottle])
def initialize(request):
    pkg = None
    credits = None
    if request.data.get("package"):
        pkg = CreditPackage.objects.filter(pk=request.data.get("package"), is_active=True).first()
        if not pkg:
            raise NotFound("Package not found.")
    else:
        try:
            credits = int(request.data.get("credits"))
        except (TypeError, ValueError):
            credits = None
        lo, hi = settings.CUSTOM_CREDITS_MIN, settings.CUSTOM_CREDITS_MAX
        if credits is None or not (lo <= credits <= hi) or str(request.data.get("credits")).strip() != str(credits):
            return Response({"detail": f"Enter a whole number of credits between {lo:,} and {hi:,}.",
                             "code": "invalid_credits"}, status=400)
    try:
        payment = services.initialize_payment(request.user, pkg, request, credits=credits)
    except paystack.PaystackError:
        logger.exception("paystack init failed")
        return Response({"detail": "We couldn't reach the payment provider. Please try again."}, status=502)
    return Response(PaymentSerializer(payment).data, status=201)


@api_view(["POST", "GET"])
@throttle_classes([PaymentThrottle])
def verify(request, reference):
    payment = Payment.objects.filter(reference=reference, user=request.user).select_related("package").first()
    if not payment:
        raise NotFound()
    try:
        payment = services.verify_payment(payment)
    except services.PaymentVerificationError as e:
        logger.error("verification mismatch %s: %s", reference, e)
        return Response({"detail": "Payment could not be verified. Contact support with your reference."}, status=409)
    except paystack.PaystackError:
        return Response({**PaymentSerializer(payment).data, "detail": "Still confirming with the bank…"}, status=202)
    return Response(PaymentSerializer(payment).data)


@api_view(["POST"])
def sandbox_complete(request, reference):
    """DEVELOPMENT ONLY. Simulates a provider confirmation when Paystack keys are
    not configured. Disabled whenever DEBUG is off or a Paystack key exists."""
    if not settings.PAYMENTS_DEV_SANDBOX:
        raise NotFound()
    payment = Payment.objects.filter(reference=reference, user=request.user,
                                     provider=Payment.Provider.DEV_SANDBOX).first()
    if not payment:
        raise NotFound()
    outcome = request.data.get("outcome", "success")
    if outcome == "success":
        payment = services.fulfil_payment(payment, {"reference": reference, "amount": payment.amount_kobo,
                                                    "currency": "NGN", "channel": "dev_sandbox",
                                                    "gateway_response": "Development sandbox approval"})
    else:
        Payment.objects.filter(pk=payment.pk, status="pending").update(status="failed",
                                                                      gateway_response="Development sandbox decline")
        payment.refresh_from_db()
    return Response(PaymentSerializer(payment).data)


class PaymentList(generics.ListAPIView):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related("package")


@api_view(["GET"])
def receipt(request, reference):
    p = Payment.objects.filter(reference=reference, user=request.user, status__in=["success", "refunded"]).select_related("package").first()
    if not p:
        raise NotFound()
    return Response({**PaymentSerializer(p).data, "email": request.user.email, "name": request.user.full_name,
                     "transaction_id": p.credit_transaction_id})


@csrf_exempt
def paystack_webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)
    raw = request.body
    if not paystack.valid_signature(raw, request.headers.get("X-Paystack-Signature")):
        return HttpResponse(status=401)
    try:
        body = json.loads(raw)
    except ValueError:
        return HttpResponse(status=400)
    event = body.get("event", "")
    data = body.get("data") or {}
    ref = data.get("reference") or (data.get("transaction") or {}).get("reference") or ""
    event_id = f"{event}:{data.get('id') or ref}"
    try:
        evt = WebhookEvent.objects.create(provider="paystack", event=event, event_id=event_id[:120], payload=body)
    except IntegrityError:
        return HttpResponse(status=200)  # duplicate delivery — already handled
    try:
        payment = Payment.objects.filter(reference=ref).first() if ref else None
        if payment and event == "charge.success":
            # Never trust the webhook body alone: re-verify with Paystack.
            services.verify_payment(payment)
        elif payment and event in ("refund.processed", "charge.dispute.create"):
            services.refund_payment(payment, "refunded" if event.startswith("refund") else "charged back")
        evt.processed_at = timezone.now()
        evt.save(update_fields=["processed_at"])
    except Exception as e:  # keep 200 so Paystack doesn't hammer us; we have the record
        logger.exception("webhook processing failed")
        evt.error = str(e)[:500]
        evt.save(update_fields=["error"])
    return HttpResponse(status=200)
