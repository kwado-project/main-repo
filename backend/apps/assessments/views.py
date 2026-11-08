from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.examinations.models import StudentExam, Subject, Topic
from apps.learning.models import Lesson
from apps.questions.models import AnswerKey

from . import services
from .models import QuizAttempt
from .serializers import AttemptSerializer, StartAttemptSerializer, question_payload


class AttemptViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AttemptSerializer

    def get_queryset(self):
        # Ownership enforced server-side: a student only ever sees their own attempts.
        qs = QuizAttempt.objects.filter(user=self.request.user).select_related("subject", "topic")
        if self.action == "list":
            qs = qs.filter(status="submitted")
        return qs

    def _payload(self, attempt):
        answers = list(attempt.answers.select_related("question__topic", "question__subject", "question__passage")
                       .prefetch_related("question__options"))
        submitted = attempt.status == "submitted"
        key_map = dict(AnswerKey.objects.filter(question_id__in=[a.question_id for a in answers])
                       .values_list("question_id", "correct_option_id")) if (submitted or attempt.mode == "practice") else {}
        qs = [question_payload(a, submitted or (attempt.mode == "practice" and a.selected_option_id is not None), key_map)
              for a in answers]
        return {**AttemptSerializer(attempt).data, "questions": qs}

    def retrieve(self, request, *args, **kwargs):
        return Response(self._payload(self.get_object()))

    def create(self, request):
        s = StartAttemptSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user = request.user

        def get(model, pk, **kw):
            if not pk:
                return None
            obj = model.objects.filter(pk=pk, **kw).first()
            if not obj:
                raise NotFound(f"{model.__name__} not found.")
            return obj

        se = get(StudentExam, d.get("student_exam"), user=user) or user.profile.active_student_exam
        attempt = services.start_attempt(
            user, kind=d["kind"], student_exam=se, subject=get(Subject, d.get("subject")),
            topic=get(Topic, d.get("topic")), lesson=get(Lesson, d.get("lesson"), is_published=True),
            mode=d.get("mode"), idempotency_key=d.get("idempotency_key"),
        )
        return Response(self._payload(attempt), status=201)

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        attempt = self.get_object()
        sa = services.answer(attempt, int(request.data.get("question", 0)), request.data.get("option"),
                             request.data.get("time_spent", 0))
        reveal = attempt.mode == "practice"
        key_map = {}
        if reveal:
            key_map = {sa.question_id: AnswerKey.objects.filter(question_id=sa.question_id)
                       .values_list("correct_option_id", flat=True).first()}
        attempt.refresh_from_db(fields=["hearts_remaining"])
        return Response({"question": question_payload(sa, reveal, key_map), "hearts_remaining": attempt.hearts_remaining})

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        attempt = self.get_object()
        updated = attempt.answers.filter(question_id=request.data.get("question")).update(
            flagged=bool(request.data.get("flagged", True)))
        if not updated:
            raise NotFound()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        attempt = services.submit(self.get_object())
        return Response(self._payload(attempt))


@api_view(["GET"])
def progress(request):
    se = request.user.profile.active_student_exam
    se_id = request.query_params.get("student_exam")
    if se_id:
        se = StudentExam.objects.filter(pk=se_id, user=request.user).first()
    if not se:
        return Response([])
    return Response(services.subject_progress(request.user, se))


@api_view(["GET"])
def topic_mastery(request, subject_id):
    from .models import TopicMastery

    tms = {t.topic_id: t for t in TopicMastery.objects.filter(user=request.user, subject_id=subject_id)}
    out = []
    for t in Topic.objects.filter(subject_id=subject_id, is_active=True, parent__isnull=True):
        tm = tms.get(t.id)
        out.append({"id": t.id, "name": t.name, "slug": t.slug, "description": t.description,
                    "mastery": round(tm.mastery * 100) if tm else None, "attempts": tm.attempts if tm else 0,
                    "lessons": t.lessons.filter(is_published=True).count()})
    return Response(out)
