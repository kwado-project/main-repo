import json
import logging
import uuid

from django.db.models import Sum
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.throttling import FlexUserThrottle as UserRateThrottle

from apps.assessments.models import StudentAnswer
from apps.core.exceptions import ServiceUnavailable
from apps.core.services import ai
from apps.examinations.models import Subject, Topic
from apps.gamification.services import bump_mission
from apps.questions.models import AnswerKey, Question
from apps.wallet import services as wallet

from .models import AIConfig, AIConversation, AIMessage, AIUsage
from .prompts import PURPOSE_INSTRUCTIONS, TUTOR_SYSTEM
from .retrieval import retrieve

logger = logging.getLogger("kwado.ai")

ACTIVITY_FOR_PURPOSE = {"tutor_chat": "ai_tutor_response", "topic_explanation": "ai_topic_explanation",
                        "practice_set": "ai_practice_set"}
HISTORY_TURNS = 12


class AIThrottle(UserRateThrottle):
    scope = "ai"


class ConversationSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", default=None, read_only=True)
    topic_name = serializers.CharField(source="topic.name", default=None, read_only=True)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=False, allow_null=True)
    topic = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.all(), required=False, allow_null=True)
    question = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.filter(status="published"), required=False, allow_null=True)

    class Meta:
        model = AIConversation
        fields = ("id", "title", "subject", "subject_name", "topic", "topic_name", "question", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


def _sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _context(conv: AIConversation, user, query: str) -> str:
    parts = []
    se = conv.student_exam or user.profile.active_student_exam
    if se:
        parts.append(f"Student context: preparing for {se.examination.name}"
                     + (f" on {se.exam_date:%d %B %Y}" if se.exam_date else "")
                     + f"; subjects: {', '.join(se.subjects.values_list('name', flat=True))}.")
    if conv.subject:
        parts.append(f"Current subject: {conv.subject.name}." + (f" Topic: {conv.topic.name}." if conv.topic else ""))
    if conv.question_id:
        q = Question.objects.prefetch_related("options").get(pk=conv.question_id)
        key = AnswerKey.objects.filter(question=q).select_related("correct_option").first()
        opts = "\n".join(f"{o.label}. {o.text}" for o in q.options.all())
        parts.append(f"Question the student is asking about:\n{q.text}\n{opts}")
        if key and key.is_verified:
            parts.append(f"VERIFIED ANSWER KEY: {key.correct_option.label}. {key.correct_option.text}")
            if q.explanation:
                parts.append(f"Verified explanation: {q.explanation}")
        mine = (StudentAnswer.objects.filter(attempt__user=user, question=q, selected_option__isnull=False)
                .select_related("selected_option").order_by("-answered_at").first())
        if mine:
            parts.append(f"The student chose: {mine.selected_option.label}. {mine.selected_option.text}")
    rag = retrieve(user, query, conv.subject_id)
    if rag:
        parts.append("Relevant excerpts:\n" + rag)
    return "\n\n".join(parts)


class ConversationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                          mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return AIConversation.objects.filter(user=self.request.user, is_archived=False).select_related("subject", "topic")

    def perform_create(self, serializer):
        title = serializer.validated_data.get("title") or "New conversation"
        serializer.save(user=self.request.user, student_exam=self.request.user.profile.active_student_exam, title=title)

    def perform_destroy(self, instance):
        instance.is_archived = True
        instance.save(update_fields=["is_archived"])

    def retrieve(self, request, *args, **kwargs):
        conv = self.get_object()
        msgs = [{"id": m.id, "role": m.role, "content": m.content, "status": m.status, "created_at": m.created_at,
                 "credits_charged": m.credits_charged, "is_mock": m.is_mock} for m in conv.messages.all()]
        return Response({**ConversationSerializer(conv).data, "messages": msgs})

    @action(detail=True, methods=["post"], throttle_classes=[AIThrottle])
    def messages(self, request, pk=None):
        conv = self.get_object()
        content = (request.data.get("content") or "").strip()
        purpose = request.data.get("purpose", "tutor_chat")
        if purpose not in ACTIVITY_FOR_PURPOSE:
            purpose = "tutor_chat"
        if not content or len(content) > 4000:
            return Response({"detail": "Write a message of up to 4,000 characters."}, status=400)
        cfg = AIConfig.get_cached(purpose)
        if cfg and not cfg.get("is_enabled", True):
            raise ServiceUnavailable()
        limit = (cfg or {}).get("daily_user_limit", 200)
        used = AIUsage.objects.filter(user=request.user, created_at__date=timezone.localdate(), succeeded=True).count()
        if used >= limit:
            return Response({"detail": "You've reached today's AI tutor limit. It resets at midnight.",
                             "code": "daily_limit"}, status=429)

        idem = (request.data.get("idempotency_key") or uuid.uuid4().hex)[:64]
        activity = ACTIVITY_FOR_PURPOSE[purpose]
        # Hold credits up-front (raises 402 before any streaming if balance is short).
        charge = wallet.charge_activity(request.user, activity, f"ai:{request.user.pk}:{idem}",
                                        reference_type="ai_conversation", reference_id=str(conv.pk))
        user_msg = AIMessage.objects.create(conversation=conv, role="user", content=content)
        if conv.title == "New conversation":
            conv.title = content[:80]
        conv.save(update_fields=["title", "updated_at"])

        history = list(conv.messages.filter(status="complete").order_by("-created_at", "-id")[: HISTORY_TURNS * 2])[::-1]
        messages = [{"role": m.role, "content": m.content} for m in history]
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        if PURPOSE_INSTRUCTIONS.get(purpose):
            messages[-1] = {"role": "user", "content": f"{content}\n\n({PURPOSE_INSTRUCTIONS[purpose]})"}
        ctx = _context(conv, request.user, content)
        user = request.user

        def stream():
            parts, finished = [], False
            yield _sse("meta", {"credits_charged": charge.credits, "user_message_id": user_msg.id})
            try:
                for chunk in ai.stream_completion(purpose=purpose, system=TUTOR_SYSTEM, context=ctx, messages=messages):
                    if isinstance(chunk, ai.AIResult):
                        msg = AIMessage.objects.create(
                            conversation=conv, role="assistant", content=chunk.text, model=chunk.model,
                            credits_charged=charge.credits, input_tokens=chunk.input_tokens,
                            output_tokens=chunk.output_tokens, is_mock=chunk.is_mock)
                        AIUsage.objects.create(user=user, purpose=purpose, model=chunk.model,
                                               input_tokens=chunk.input_tokens, output_tokens=chunk.output_tokens,
                                               cache_read_tokens=chunk.cache_read_tokens)
                        finished = True
                        bump_mission(user, "tutor_questions", 1)
                        yield _sse("done", {"message_id": msg.id, "balance": wallet.get_wallet(user).balance,
                                            "is_mock": chunk.is_mock, "suggestions": _suggestions(conv, purpose)})
                    else:
                        parts.append(chunk)
                        yield _sse("delta", {"text": chunk})
            except ai.AIError as e:
                AIUsage.objects.create(user=user, purpose=purpose, model="", succeeded=False, error=str(e)[:60])
            finally:
                if not finished and charge.transaction:
                    # Failed, refused, or client disconnected: never charge for an incomplete answer.
                    wallet.refund(charge.transaction, "AI response did not complete")
                    AIMessage.objects.filter(pk=user_msg.pk).update(status="failed")
            if not finished:
                yield _sse("error", {"detail": "The tutor couldn't finish that answer. Your credits were refunded.",
                                     "balance": wallet.get_wallet(user).balance, "refunded": charge.credits})

        resp = StreamingHttpResponse(stream(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp


def _suggestions(conv, purpose):
    topic = conv.topic.name if conv.topic else "this topic"
    if conv.question_id:
        return ["Show me a similar question", "What's the common mistake here?", "Explain the concept behind it"]
    if purpose == "practice_set":
        return ["Explain question 1 step by step", "Make them harder", f"Teach me {topic} from the basics"]
    return ["Give me an example", "Test me with 3 questions", "Explain it more simply"]
