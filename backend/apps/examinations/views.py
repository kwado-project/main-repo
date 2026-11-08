from django.db import IntegrityError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.db import read_db

from .models import Examination, StudentExam, Subject, Topic
from .serializers import ExaminationSerializer, StudentExamSerializer, SubjectSerializer, TopicSerializer


class ExaminationViewSet(viewsets.ReadOnlyModelViewSet):
    """Public catalogue (cached at the CDN/edge; read replica)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ExaminationSerializer
    pagination_class = None
    lookup_field = "code"

    def get_queryset(self):
        return (Examination.objects.using(read_db()).filter(is_active=True)
                .prefetch_related("exam_subjects__subject"))


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = SubjectSerializer
    pagination_class = None
    queryset = Subject.objects.filter(is_active=True)

    @action(detail=True)
    def topics(self, request, pk=None):
        qs = Topic.objects.using(read_db()).filter(subject_id=pk, is_active=True, parent__isnull=True)
        return Response(TopicSerializer(qs, many=True).data)


class StudentExamViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = StudentExamSerializer
    pagination_class = None

    def get_queryset(self):
        return (StudentExam.objects.filter(user=self.request.user, is_archived=False)
                .select_related("examination").prefetch_related("subjects", "examination__exam_subjects__subject"))

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        existing = StudentExam.objects.filter(user=request.user, examination=s.validated_data["examination"]).first()
        if existing:
            if existing.is_archived:
                existing.is_archived = False
                existing.save(update_fields=["is_archived"])
            return Response(self.get_serializer(existing).data, status=200)
        try:
            se = s.save(user=request.user)
        except IntegrityError:
            return Response({"detail": "You already have this examination."}, status=400)
        profile = request.user.profile
        profile.active_student_exam = se
        profile.save(update_fields=["active_student_exam"])
        return Response(self.get_serializer(se).data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        se = serializer.save()
        steps = ["date", "subjects", "study_time", "diagnostic", "roadmap", "done"]
        req_step = self.request.data.get("onboarding_step")
        if req_step in steps and steps.index(req_step) > steps.index(se.onboarding_step):
            se.onboarding_step = req_step
            se.save(update_fields=["onboarding_step"])

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        se = self.get_object()
        se.is_archived = True
        se.save(update_fields=["is_archived"])
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        se = self.get_object()
        request.user.profile.active_student_exam = se
        request.user.profile.save(update_fields=["active_student_exam"])
        return Response(self.get_serializer(se).data)
