import hashlib
import uuid

from django.conf import settings
from django.http import HttpResponse
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.core.exceptions import InsufficientCredits
from apps.core.services import storage
from apps.examinations.models import Subject
from apps.wallet.services import get_wallet, price_of

from .extract import InvalidFile, safe_name, validate
from .models import StudyMaterial
from .tasks import analyse_material, process_material


class MaterialSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", default=None)

    class Meta:
        model = StudyMaterial
        fields = ("id", "title", "filename", "content_type", "size_bytes", "status", "subject", "subject_name",
                  "extracted_chars", "analysis", "error", "created_at")


class MaterialViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    serializer_class = MaterialSerializer
    parser_classes = [MultiPartParser]
    pagination_class = None

    def get_queryset(self):
        # Private by default: owners only.
        return StudyMaterial.objects.filter(owner=self.request.user).select_related("subject")

    def create(self, request):
        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "Choose a file to upload."}, status=400)
        if f.size > settings.MAX_UPLOAD_BYTES:
            return Response({"detail": f"Files must be under {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB."}, status=400)
        data = f.read()
        try:
            ext, ctype = validate(f.name, data[:16])
        except InvalidFile as e:
            return Response({"detail": str(e)}, status=400)
        subject = Subject.objects.filter(pk=request.data.get("subject")).first() if request.data.get("subject") else None
        se = request.user.profile.active_student_exam
        key = f"materials/{request.user.pk}/{uuid.uuid4().hex}/{safe_name(f.name)}"
        storage.put_object(key, data, ctype)
        m = StudyMaterial.objects.create(
            owner=request.user, student_exam=se, examination=se.examination if se else None, subject=subject,
            title=(request.data.get("title") or f.name)[:200], filename=safe_name(f.name), storage_key=key,
            content_type=ctype, size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
        )
        process_material.delay(m.pk)
        m.refresh_from_db()
        return Response(MaterialSerializer(m).data, status=201)

    def perform_destroy(self, instance):
        storage.delete_object(instance.storage_key)
        instance.delete()

    @action(detail=True, methods=["post"])
    def analyse(self, request, pk=None):
        m = self.get_object()
        if m.status != "ready":
            return Response({"detail": "Wait until the file has finished processing."}, status=400)
        if get_wallet(request.user).balance < price_of("document_analysis"):
            raise InsufficientCredits()
        analyse_material.delay(m.pk, (request.data.get("idempotency_key") or uuid.uuid4().hex)[:40])
        m.refresh_from_db()
        return Response(MaterialSerializer(m).data, status=202)

    @action(detail=True)
    def download(self, request, pk=None):
        m = self.get_object()
        url = storage.presigned_download_url(m.storage_key, m.filename)
        if url:
            return Response({"url": url})
        resp = HttpResponse(storage.get_object(m.storage_key), content_type=m.content_type)
        resp["Content-Disposition"] = f'attachment; filename="{m.filename}"'
        return resp
