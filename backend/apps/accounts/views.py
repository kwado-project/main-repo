from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from apps.core.throttling import FlexAnonThrottle as AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.audit import audit, client_ip

from . import otp
from .models import User, normalize_email
from .serializers import MeSerializer, OTPRequestSerializer, OTPVerifySerializer
from .services import create_student
from .tasks import send_no_account_email, send_otp_email

GENERIC_SENT = "If this email can be used, we've sent a 6-digit code to it. It expires in 5 minutes."


class OTPRequestThrottle(AnonRateThrottle):
    scope = "otp_request"


class OTPVerifyThrottle(AnonRateThrottle):
    scope = "otp_verify"


def _issue_tokens(user, response):
    refresh = RefreshToken.for_user(user)
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME, str(refresh), max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True, secure=settings.REFRESH_COOKIE_SECURE, samesite=settings.REFRESH_COOKIE_SAMESITE, path="/api/auth/",
    )
    response.data["access"] = str(refresh.access_token)
    return response


class RequestOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPRequestThrottle]

    def post(self, request):
        s = OTPRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = normalize_email(s.validated_data["email"])
        intent = s.validated_data["intent"]
        wait = otp.cooldown_remaining(email)
        payload = {"detail": GENERIC_SENT, "resend_in": settings.OTP_RESEND_COOLDOWN_SECONDS}
        if wait > 0:
            return Response({"detail": f"Please wait {wait}s before requesting another code.",
                             "code": "cooldown", "resend_in": wait}, status=429)
        user = User.objects.filter(email=email).first()
        if user and not user.is_active:
            return Response(payload)  # generic: do not reveal suspended accounts
        if user:
            purpose = "login"
        elif intent == "register":
            purpose = "register"
        else:
            # Unknown email on the login screen: tell the inbox owner, not the requester.
            otp.issue(email, "login", ip=client_ip(request))  # keeps cooldown behaviour identical
            send_no_account_email.delay(email)
            return Response(payload)
        code = otp.issue(email, purpose, referral_code=s.validated_data.get("referral_code", ""), ip=client_ip(request))
        send_otp_email.delay(email, code, purpose)
        if settings.OTP_DEV_ECHO:
            payload["dev_code"] = code  # development only — never present in production
        return Response(payload)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        s = OTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        email = normalize_email(s.validated_data["email"])
        try:
            record = otp.verify(email, s.validated_data["code"])
        except otp.OTPError as e:
            return Response({"detail": e.message, "code": e.code}, status=400)
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=email).first()
            is_new = False
            if user is None:
                if record.purpose != "register":
                    return Response({"detail": "No account found for this email.", "code": "no_account"}, status=400)
                user = create_student(email, referral_code=record.referral_code, ip=client_ip(request), request=request)
                if s.validated_data.get("full_name"):
                    user.full_name = s.validated_data["full_name"]
                    user.save(update_fields=["full_name"])
                is_new = True
        if not user.is_active:
            return Response({"detail": "This account is not active.", "code": "inactive"}, status=403)
        audit("auth.login", actor=user, target=user, request=request, new=is_new)
        resp = Response({"is_new": is_new, "user": MeSerializer(user).data})
        return _issue_tokens(user, resp)


class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            return Response({"detail": "Not signed in.", "code": "no_session"}, status=401)
        try:
            old = RefreshToken(raw)
            user = User.objects.get(pk=old["user_id"], is_active=True)
            old.blacklist()  # rotation: each refresh token is single-use
        except (TokenError, User.DoesNotExist):
            resp = Response({"detail": "Session expired.", "code": "session_expired"}, status=401)
            resp.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/auth/")
            return resp
        return _issue_tokens(user, Response({}))


class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        resp = Response(status=status.HTTP_204_NO_CONTENT)
        resp.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/auth/")
        return resp


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = User.objects.select_related("profile", "wallet").get(pk=request.user.pk)
        return Response(MeSerializer(user).data)

    def patch(self, request):
        user = User.objects.select_related("profile", "wallet").get(pk=request.user.pk)
        s = MeSerializer(user, data=request.data, partial=True, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(MeSerializer(user).data)
