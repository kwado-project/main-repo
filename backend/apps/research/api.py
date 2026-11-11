"""Admin API for the research pipeline (/api/admin-api/research/...)."""
import json

from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.core.audit import audit
from apps.core.permissions import IsAdmin, IsContentManager

from . import pipeline, promote, reports, review
from .extraction.structure import to_record
from .models import CopyrightPermission, ExtractionJob, PastQuestion, Source, SourceDocument

P = Source.Permission


class SourceSer(serializers.ModelSerializer):
    documents = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    may_extract = serializers.BooleanField(read_only=True)

    def get_documents(self, s):
        return getattr(s, "documents_count", None)

    def get_questions(self, s):
        return getattr(s, "questions_count", None)

    class Meta:
        model = Source
        exclude = ("robots_txt",)


class PermissionSer(serializers.ModelSerializer):
    class Meta:
        model = CopyrightPermission
        exclude = ("source",)
        read_only_fields = ("recorded_by",)


class SourceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsContentManager]
    serializer_class = SourceSer
    filterset_fields = ("permission_status", "is_seed", "is_active")
    search_fields = ("domain", "name")
    ordering_fields = ("domain", "created_at")

    def get_queryset(self):
        from django.db.models import Count
        return (Source.objects.annotate(documents_count=Count("documents", distinct=True), questions_count=Count("questions", distinct=True))
                .order_by("-documents_count", "domain"))

    def retrieve(self, request, pk=None):
        s = self.get_object()
        return Response({**SourceSer(s).data, "robots_txt": s.robots_txt[:5000],
                         "permissions": PermissionSer(s.permissions.all(), many=True).data})

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def permission(self, request, pk=None):
        """Record a human copyright decision. This is the ONLY way a source becomes extractable."""
        s = self.get_object()
        decision = request.data.get("status")
        mapping = {"permitted": (P.PERMITTED, "granted"), "open_license": (P.OPEN_LICENSE, "granted"),
                   "denied": (P.DENIED, "denied"), "requested": (P.NEEDS_REVIEW, "requested")}
        if decision not in mapping:
            raise ValidationError({"status": "Use permitted, open_license, denied or requested."})
        evidence = (request.data.get("evidence") or "").strip()
        if decision in ("permitted", "open_license") and not evidence:
            raise ValidationError({"evidence": "Record the evidence: licence text, link or the permission email."})
        perm_status, record_status = mapping[decision]
        with transaction.atomic():
            perm = CopyrightPermission.objects.create(
                source=s, status=record_status, basis=request.data.get("basis", decision)[:40],
                scope=(request.data.get("scope") or "")[:255], evidence=evidence, contact=(request.data.get("contact") or "")[:200],
                valid_until=request.data.get("valid_until") or None, recorded_by=request.user)
            s.permission_status = perm_status
            if request.data.get("license_name"):
                s.license_name = request.data["license_name"][:120]
            s.save(update_fields=["permission_status", "license_name", "updated_at"])
            rights = {P.PERMITTED: "cleared", P.OPEN_LICENSE: "cleared", P.DENIED: "denied"}.get(perm_status, "permission_pending")
            PastQuestion.objects.filter(source=s).update(rights_status=rights)
        audit("research.permission", actor=request.user, target=s, request=request, decision=decision, permission_id=perm.pk)
        return Response({**SourceSer(s).data, "permission": PermissionSer(perm).data})

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def active(self, request, pk=None):
        s = self.get_object()
        s.is_active = bool(request.data.get("is_active"))
        s.save(update_fields=["is_active", "updated_at"])
        return Response({"is_active": s.is_active})

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def check(self, request, pk=None):
        return Response(pipeline.check_source(self.get_object(), force=True))


class DocumentSer(serializers.ModelSerializer):
    source_domain = serializers.CharField(source="source.domain")
    subject_name = serializers.CharField(source="subject.name", default=None)

    class Meta:
        model = SourceDocument
        fields = ("id", "url", "kind", "title", "source", "source_domain", "subject", "subject_name", "year",
                  "examination_guess", "classification_confidence", "status", "status_reason", "discovered_via", "created_at")


class DocumentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsContentManager]
    serializer_class = DocumentSer
    filterset_fields = ("status", "source", "subject", "year", "kind")
    search_fields = ("url", "title")

    def get_queryset(self):
        return SourceDocument.objects.select_related("source", "subject").order_by("-created_at")


class QuestionListSer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", default=None)
    source_domain = serializers.CharField(source="source.domain")
    options = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()

    class Meta:
        model = PastQuestion
        fields = ("id", "year", "subject", "subject_name", "question_number", "text", "passage", "options", "answers",
                  "topic", "difficulty", "has_math", "has_diagram", "image_refs", "source_domain", "source_url",
                  "page_number", "extraction_method", "extraction_confidence", "verification_status", "rights_status",
                  "duplicate_of", "flags", "promoted_question")

    def get_options(self, q):
        return {o.label: o.text for o in q.options.all()}

    def get_answers(self, q):
        return [{"label": a.label, "origin": a.origin, "confidence": a.confidence, "note": a.note} for a in q.answers.all()]


class QuestionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsContentManager]
    serializer_class = QuestionListSer
    filterset_fields = ("subject", "year", "topic", "difficulty", "verification_status", "rights_status", "source")
    search_fields = ("text",)

    def get_queryset(self):
        qs = (PastQuestion.objects.select_related("subject", "source")
              .prefetch_related("options", "answers").order_by("year", "subject__name", "question_number"))
        if self.request.query_params.get("include_duplicates") != "1":
            qs = qs.filter(duplicate_of__isnull=True)
        if self.request.query_params.get("awaiting") == "1":
            # The human work queue: flagged questions first, then ones that passed automatic checks.
            from django.db.models import Case, IntegerField, Value, When
            V = PastQuestion.Verification
            qs = (qs.filter(verification_status__in=[V.NEEDS_REVIEW, V.AUTO_CHECKED, V.UNVERIFIED])
                  .annotate(_p=Case(When(verification_status=V.NEEDS_REVIEW, then=Value(0)), default=Value(1), output_field=IntegerField()))
                  .order_by("_p", "year", "subject__name", "question_number"))
        return qs

    def retrieve(self, request, pk=None):
        q = self.get_object()
        return Response({**QuestionListSer(q).data,
                         "explanations": [{"text": e.text, "origin": e.origin} for e in q.explanations.all()],
                         "verifications": [{"check": v.check_name, "result": v.result, "actor": v.actor, "details": v.details,
                                            "at": v.created_at} for v in q.verifications.all()],
                         "duplicates": list(q.duplicates.values("id", "source__domain", "source_url"))})

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        try:
            q = review.mark_verified(self.get_object(), request.user, request.data.get("answer"), request.data.get("note", ""))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response(QuestionListSer(q).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        try:
            q = review.mark_rejected(self.get_object(), request.user, request.data.get("reason", ""))
        except ValueError as e:
            raise ValidationError({"detail": str(e)})
        return Response(QuestionListSer(q).data)

    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        """Set metadata used for filtering (topic, difficulty). The question text is never edited."""
        q = self.get_object()
        if "topic" in request.data:
            q.topic_id = request.data.get("topic") or None
        if "difficulty" in request.data:
            d = request.data.get("difficulty")
            if d not in (None, "", 1, 2, 3, "1", "2", "3"):
                raise ValidationError({"difficulty": "Use 1, 2 or 3."})
            q.difficulty = int(d) if d else None
        q.save(update_fields=["topic", "difficulty", "updated_at"])
        return Response(QuestionListSer(q).data)

    @action(detail=True, methods=["post"])
    def promote(self, request, pk=None):
        try:
            bank = promote.promote(self.get_object(), request.user)
        except promote.NotEligible as e:
            raise ValidationError({"detail": str(e)})
        audit("research.promote", actor=request.user, target=bank, request=request, research_question=pk)
        return Response({"question_bank_id": bank.pk, "status": bank.status})

    @action(detail=False)
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset()).prefetch_related("explanations")[:20000]
        data = json.dumps([to_record(q) for q in qs], ensure_ascii=False, indent=1)
        resp = HttpResponse(data, content_type="application/json")
        resp["Content-Disposition"] = f'attachment; filename="jamb-past-questions-{timezone.localdate()}.json"'
        return resp


@api_view(["GET"])
@permission_classes([IsContentManager])
def overview(request):
    return Response(reports.coverage(request.query_params.get("exam", "jamb")))


@api_view(["GET"])
@permission_classes([IsAdmin])
def job_list(request):
    qs = ExtractionJob.objects.select_related("document", "source").order_by("-updated_at")
    if s := request.query_params.get("status"):
        qs = qs.filter(status=s)
    return Response([{"id": j.id, "kind": j.kind, "status": j.status, "key": j.idempotency_key, "attempts": j.attempts,
                      "source": getattr(j.source, "domain", None), "document": getattr(j.document, "url", None),
                      "error": j.error[:500], "result": j.result, "updated_at": j.updated_at} for j in qs[:100]])


@api_view(["POST"])
@permission_classes([IsAdmin])
def run(request):
    """Queue pipeline work on the research worker."""
    from . import tasks

    what = request.data.get("action", "cycle")
    if what == "cycle":
        r = tasks.research_cycle.delay()
    elif what == "verify":
        r = tasks.verify_pending_task.delay()
    elif what == "matrix":
        from . import matrix
        return Response(matrix.ensure_matrix(request.data.get("exam", "jamb")))
    else:
        raise ValidationError({"action": "Use cycle, verify or matrix."})
    audit("research.run", actor=request.user, request=request, run=what)
    return Response({"queued": what, "task_id": r.id}, status=202)


@api_view(["POST"])
@permission_classes([IsAdmin])
def add_seed(request):
    url = (request.data.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValidationError({"url": "Enter a full URL starting with https://"})
    s = pipeline.add_seed(url, request.data.get("name", ""))
    return Response(SourceSer(s).data, status=201)
