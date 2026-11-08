"""Admin & content-manager API (separate from the student API)."""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.accounts.models import User
from apps.ai_tutor.models import AIConfig, AIUsage
from apps.assessments.models import QuizAttempt
from apps.core.audit import audit
from apps.core.db import read_db
from apps.core.models import AuditLog, SystemSetting
from apps.core.permissions import IsAdmin, IsContentManager
from apps.examinations.models import Examination, ExamSubject, Subject, Topic
from apps.learning.models import LearningPath, LearningPathNode, Lesson
from apps.materials.models import StudyMaterial
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.payments.services import refund_payment, verify_payment
from apps.questions.models import Question, QuestionOption
from apps.questions.services import import_rows, transition
from apps.referrals.models import ReferralReward
from apps.wallet import services as wallet
from apps.wallet.models import ActivityPricing, CreditPackage, CreditTransaction


def model_serializer(m, fields="__all__", ro=()):
    meta = type("Meta", (), {"model": m, "fields": fields, "read_only_fields": ro})
    return type(f"{m.__name__}AdminSerializer", (serializers.ModelSerializer,), {"Meta": meta})


def crud(m, perm, *, search=(), filters=(), ordering=("-id",), ser=None, qs=None):
    class VS(viewsets.ModelViewSet):
        permission_classes = [perm]
        serializer_class = ser or model_serializer(m)
        search_fields = search
        filterset_fields = filters
        ordering_fields = "__all__"

        def get_queryset(self):
            return (qs() if qs else m.objects.all()).order_by(*ordering)

        def perform_destroy(self, instance):
            audit(f"admin.delete.{m.__name__}", actor=self.request.user, target=instance, request=self.request)
            instance.delete()

    VS.__name__ = f"{m.__name__}AdminViewSet"
    return VS


# ---------------------------------------------------------------- content
ExaminationVS = crud(Examination, IsContentManager, search=("name", "code"), ordering=("order",),
                     ser=model_serializer(Examination, [f.name for f in Examination._meta.concrete_fields]))
ExamSubjectVS = crud(ExamSubject, IsContentManager, filters=("examination",), ordering=("examination", "id"))
SubjectVS = crud(Subject, IsContentManager, search=("name",), ordering=("name",))
TopicVS = crud(Topic, IsContentManager, search=("name",), filters=("subject", "parent"), ordering=("subject", "order"))
LessonVS = crud(Lesson, IsContentManager, search=("title",), filters=("topic", "is_published"), ordering=("topic", "order"))
LearningPathVS = crud(LearningPath, IsContentManager, filters=("subject", "examination"))
LearningPathNodeVS = crud(LearningPathNode, IsContentManager, filters=("path",), ordering=("path", "order"))


class OptionSer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ("id", "label", "text", "order")


class QuestionAdminSer(serializers.ModelSerializer):
    options = OptionSer(many=True)
    correct_option = serializers.IntegerField(source="answer_key.correct_option_id", read_only=True, default=None)
    answer_verified_by = serializers.CharField(source="answer_key.verified_by.email", read_only=True, default=None)
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    topic_name = serializers.CharField(source="topic.name", read_only=True, default=None)

    class Meta:
        model = Question
        fields = "__all__"
        read_only_fields = ("status", "created_by", "reviewed_by", "published_at")

    def create(self, data):
        opts = data.pop("options")
        q = Question.objects.create(**data, created_by=self.context["request"].user)
        for i, o in enumerate(opts):
            QuestionOption.objects.create(question=q, order=o.get("order", i), label=o["label"], text=o["text"])
        return q

    def update(self, q, data):
        opts = data.pop("options", None)
        if q.status == Question.Status.PUBLISHED:
            raise serializers.ValidationError("Unpublish (move to draft) before editing a published question.")
        for k, v in data.items():
            setattr(q, k, v)
        q.save()
        if opts is not None:
            if hasattr(q, "answer_key"):
                q.answer_key.delete()  # options changed → answer must be re-verified
                q.status = Question.Status.DRAFT
                q.save(update_fields=["status"])
            q.options.all().delete()
            for i, o in enumerate(opts):
                QuestionOption.objects.create(question=q, order=o.get("order", i), label=o["label"], text=o["text"])
        return q


class QuestionVS(crud(Question, IsContentManager, search=("text",), ser=QuestionAdminSer,
                      filters=("subject", "topic", "status", "examination", "is_ai_generated", "difficulty"),
                      qs=lambda: Question.objects.select_related("subject", "topic", "answer_key__verified_by")
                      .prefetch_related("options"))):
    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        q = transition(self.get_object(), request.data.get("status"), request.user,
                       correct_option_id=request.data.get("correct_option"), notes=request.data.get("notes", ""),
                       source=request.data.get("source", ""))
        return Response(QuestionAdminSer(q).data)

    @action(detail=False, methods=["post"], url_path="import")
    def import_(self, request):
        rows = request.data.get("rows")
        if not isinstance(rows, list) or len(rows) > 1000:
            return Response({"detail": "Send up to 1,000 rows as a JSON list."}, status=400)
        return Response(import_rows(rows, request.user))

    @action(detail=False)
    def stats(self, request):
        return Response(dict(Question.objects.values_list("status").annotate(n=Count("id"))))


# ---------------------------------------------------------------- money
class PricingVS(crud(ActivityPricing, IsAdmin, ordering=("key",))):
    def perform_create(self, s):
        s.save(); wallet.invalidate_pricing_cache()
        audit("admin.pricing.create", actor=self.request.user, request=self.request, data=s.data)

    def perform_update(self, s):
        s.save(); wallet.invalidate_pricing_cache()
        audit("admin.pricing.update", actor=self.request.user, request=self.request, data=s.data)


PackageVS = crud(CreditPackage, IsAdmin, ordering=("order",))
AIConfigVS = crud(AIConfig, IsAdmin, ordering=("purpose",))
SettingVS = crud(SystemSetting, IsAdmin, ordering=("key",))


class TxnSer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="wallet.user.email")

    class Meta:
        model = CreditTransaction
        fields = "__all__"


class TransactionVS(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = TxnSer
    filterset_fields = ("kind",)
    search_fields = ("wallet__user__email", "reference_id", "idempotency_key")

    def get_queryset(self):
        return CreditTransaction.objects.select_related("wallet__user")


class PaymentAdminSer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email")
    package_name = serializers.CharField(source="package.name")

    class Meta:
        model = Payment
        exclude = ("raw_verification",)


class PaymentVS(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = PaymentAdminSer
    filterset_fields = ("status", "provider")
    search_fields = ("reference", "user__email")

    def get_queryset(self):
        return Payment.objects.select_related("user", "package")

    @action(detail=True, methods=["post"])
    def reverify(self, request, pk=None):
        p = verify_payment(self.get_object())
        audit("admin.payment.reverify", actor=request.user, target=p, request=request)
        return Response(PaymentAdminSer(p).data)

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        p = refund_payment(self.get_object(), "refunded by admin")
        audit("admin.payment.refund", actor=request.user, target=p, request=request)
        return Response(PaymentAdminSer(p).data)


class RewardSer(serializers.ModelSerializer):
    referrer = serializers.CharField(source="referral.referrer.email")
    referred = serializers.CharField(source="referral.referred.email")
    reference = serializers.CharField(source="payment.reference")

    class Meta:
        model = ReferralReward
        fields = ("id", "referrer", "referred", "reference", "purchased_credits", "reward_credits", "status", "created_at")


class RewardVS(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = RewardSer
    filterset_fields = ("status",)
    search_fields = ("referral__referrer__email", "referral__referred__email")

    def get_queryset(self):
        return ReferralReward.objects.select_related("referral__referrer", "referral__referred", "payment").order_by("-id")


# ---------------------------------------------------------------- people
class UserAdminSer(serializers.ModelSerializer):
    balance = serializers.IntegerField(source="wallet.balance", read_only=True, default=0)
    xp = serializers.IntegerField(source="profile.total_xp", read_only=True, default=0)

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role", "is_active", "date_joined", "last_login", "referral_code",
                  "balance", "xp")
        read_only_fields = ("email", "date_joined", "last_login", "referral_code")


class UserVS(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = UserAdminSer
    filterset_fields = ("role", "is_active")
    search_fields = ("email", "full_name")
    http_method_names = ["get", "patch", "post"]

    def get_queryset(self):
        return User.objects.select_related("wallet", "profile").order_by("-id")

    def perform_update(self, s):
        before = {"role": s.instance.role, "is_active": s.instance.is_active}
        s.save()
        audit("admin.user.update", actor=self.request.user, target=s.instance, request=self.request,
              before=before, after={"role": s.instance.role, "is_active": s.instance.is_active})

    @action(detail=True, methods=["post"])
    def adjust_credits(self, request, pk=None):
        user = self.get_object()
        amount = int(request.data.get("amount", 0))
        reason = (request.data.get("reason") or "").strip()
        key = request.data.get("idempotency_key")
        if not amount or not reason or not key:
            return Response({"detail": "amount, reason and idempotency_key are required."}, status=400)
        kind = CreditTransaction.Kind.ADJUSTMENT
        fn = wallet.credit if amount > 0 else wallet.debit
        txn = fn(user, abs(amount), kind, f"admin:{key}", f"Admin adjustment — {reason}"[:255], created_by=request.user)
        audit("admin.credits.adjust", actor=request.user, target=user, request=request, amount=amount, reason=reason)
        return Response(TxnSer(txn).data)


class MaterialAdminVS(viewsets.ReadOnlyModelViewSet):
    """Metadata only — admins cannot read private student documents' contents here."""

    permission_classes = [IsAdmin]
    serializer_class = model_serializer(StudyMaterial, ("id", "title", "owner", "visibility", "status", "size_bytes",
                                                        "content_type", "created_at"))
    filterset_fields = ("status", "visibility")

    def get_queryset(self):
        return StudyMaterial.objects.order_by("-id")


class AuditVS(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = model_serializer(AuditLog)
    filterset_fields = ("action",)
    search_fields = ("action", "target_id")

    def get_queryset(self):
        return AuditLog.objects.order_by("-id")


@api_view(["POST"])
@permission_classes([IsAdmin])
def broadcast(request):
    title, body = request.data.get("title", "")[:120], request.data.get("body", "")[:255]
    if not title:
        return Response({"detail": "Title required."}, status=400)
    ids = User.objects.filter(is_active=True, role="student").values_list("id", flat=True).iterator(chunk_size=5000)
    batch, n = [], 0
    for uid in ids:
        batch.append(Notification(user_id=uid, kind="system", title=title, body=body, link=request.data.get("link", "")))
        if len(batch) >= 5000:
            Notification.objects.bulk_create(batch); n += len(batch); batch = []
    Notification.objects.bulk_create(batch); n += len(batch)
    audit("admin.broadcast", actor=request.user, request=request, title=title, recipients=n)
    return Response({"sent": n})


@api_view(["GET"])
@permission_classes([IsContentManager])
def overview(request):
    db = read_db()
    now = timezone.now()
    d30 = now - timedelta(days=30)
    users = User.objects.using(db)
    pays = Payment.objects.using(db).filter(status="success")
    signups = (users.filter(date_joined__gte=d30).annotate(d=TruncDate("date_joined")).values("d")
               .annotate(n=Count("id")).order_by("d"))
    revenue = (pays.filter(verified_at__gte=d30).annotate(d=TruncDate("verified_at")).values("d")
               .annotate(kobo=Sum("amount_kobo")).order_by("d"))
    attempts = (QuizAttempt.objects.using(db).filter(submitted_at__gte=d30).annotate(d=TruncDate("submitted_at"))
                .values("d").annotate(n=Count("id")).order_by("d"))
    from apps.gamification.models import ActivityDay
    dau = ActivityDay.objects.using(db).filter(date=timezone.localdate()).count()
    ai = AIUsage.objects.using(db).filter(created_at__gte=d30).aggregate(
        calls=Count("id"), failed=Count("id", filter=Q(succeeded=False)),
        input=Sum("input_tokens"), output=Sum("output_tokens"), cached=Sum("cache_read_tokens"))
    spend = CreditTransaction.objects.using(db).filter(kind="spend", created_at__gte=d30).values("activity_key") \
        .annotate(credits=Sum("amount")).order_by("credits")
    return Response({
        "totals": {"students": users.filter(role="student").count(), "dau": dau,
                   "revenue_naira_30d": (pays.filter(verified_at__gte=d30).aggregate(s=Sum("amount_kobo"))["s"] or 0) // 100,
                   "questions_published": Question.objects.using(db).filter(status="published").count(),
                   "pending_review": Question.objects.using(db).filter(status__in=["validated", "answer_verified", "in_review"]).count(),
                   "attempts_30d": QuizAttempt.objects.using(db).filter(submitted_at__gte=d30).count()},
        "signups": [{"date": r["d"], "value": r["n"]} for r in signups],
        "revenue": [{"date": r["d"], "value": (r["kobo"] or 0) // 100} for r in revenue],
        "attempts": [{"date": r["d"], "value": r["n"]} for r in attempts],
        "ai": ai,
        "spend_by_activity": [{"activity": r["activity_key"], "credits": -r["credits"]} for r in spend],
    })
