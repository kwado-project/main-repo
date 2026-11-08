from rest_framework import serializers

from .models import QuizAttempt, StudentAnswer


def question_payload(sa: StudentAnswer, reveal: bool, key_map: dict):
    q = sa.question
    data = {
        "id": q.id, "order": sa.order, "text": q.text, "image_url": q.image_url or None, "table": q.table_data,
        "difficulty": q.get_difficulty_display(), "topic": q.topic.name if q.topic else None,
        "subject": q.subject.name, "exam_year": q.exam_year, "is_official_past_question": q.is_official_past_question,
        "passage": {"title": q.passage.title, "body": q.passage.body} if q.passage else None,
        "options": [{"id": o.id, "label": o.label, "text": o.text} for o in q.options.all()],
        "selected_option": sa.selected_option_id, "flagged": sa.flagged, "answered": sa.selected_option_id is not None,
    }
    if reveal:
        data.update({"is_correct": sa.is_correct, "correct_option": key_map.get(q.id),
                     "explanation": q.explanation, "solution_steps": q.solution_steps})
    return data


class AttemptSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", default=None)
    topic_name = serializers.CharField(source="topic.name", default=None)
    kind_label = serializers.CharField(source="get_kind_display")
    deadline = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = ("id", "kind", "kind_label", "mode", "status", "subject", "subject_name", "topic", "topic_name",
                  "lesson", "hearts_enabled", "hearts_remaining", "time_limit_seconds", "started_at", "submitted_at",
                  "deadline", "total_questions", "correct_count", "score_percent", "time_spent_seconds", "xp_earned",
                  "credits_charged", "result_summary")

    def get_deadline(self, obj):
        if not obj.time_limit_seconds:
            return None
        from datetime import timedelta
        return obj.started_at + timedelta(seconds=obj.time_limit_seconds)

    def to_representation(self, obj):
        d = super().to_representation(obj)
        d["result_summary"] = {k: v for k, v in (obj.result_summary or {}).items() if k != "client_key"}
        return d


class StartAttemptSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=QuizAttempt.Kind.choices)
    mode = serializers.ChoiceField(choices=QuizAttempt.Mode.choices, required=False)
    student_exam = serializers.IntegerField(required=False, allow_null=True)
    subject = serializers.IntegerField(required=False, allow_null=True)
    topic = serializers.IntegerField(required=False, allow_null=True)
    lesson = serializers.IntegerField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(max_length=64, required=False)
