from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import Examination, ExamSubject, StudentExam, Subject, Topic


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ("id", "name", "slug", "icon", "color", "description")


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ("id", "subject", "parent", "name", "slug", "description", "order", "weight")


class ExamSubjectSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer()

    class Meta:
        model = ExamSubject
        fields = ("subject", "is_compulsory")


class ExaminationSerializer(serializers.ModelSerializer):
    subjects = ExamSubjectSerializer(source="exam_subjects", many=True, read_only=True)

    class Meta:
        model = Examination
        fields = ("id", "name", "code", "full_name", "description", "color", "min_subjects", "max_subjects",
                  "rules_note", "mock_duration_minutes", "subjects")


class StudentExamSerializer(serializers.ModelSerializer):
    examination = ExaminationSerializer(read_only=True)
    examination_id = serializers.PrimaryKeyRelatedField(
        source="examination", queryset=Examination.objects.filter(is_active=True), write_only=True
    )
    subjects = SubjectSerializer(many=True, read_only=True)
    subject_ids = serializers.PrimaryKeyRelatedField(
        source="subjects", queryset=Subject.objects.filter(is_active=True), many=True, write_only=True, required=False
    )
    days_left = serializers.SerializerMethodField()

    class Meta:
        model = StudentExam
        fields = ("id", "examination", "examination_id", "exam_date", "subjects", "subject_ids", "daily_minutes",
                  "study_days", "target_score", "onboarding_step", "days_left", "created_at")
        read_only_fields = ("created_at",)

    def get_days_left(self, obj):
        if not obj.exam_date:
            return None
        return max(0, (obj.exam_date - timezone.localdate()).days)

    def validate_exam_date(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("The examination date must be in the future.")
        return value

    def validate_daily_minutes(self, value):
        if not 10 <= value <= 600:
            raise serializers.ValidationError("Choose between 10 minutes and 10 hours a day.")
        return value

    def validate(self, attrs):
        exam = attrs.get("examination") or getattr(self.instance, "examination", None)
        if "subjects" in attrs and exam:
            try:
                exam.validate_subject_selection([s.id for s in attrs["subjects"]])
            except DjangoValidationError as e:
                raise serializers.ValidationError({"subject_ids": e.messages})
        if self.instance and "examination" in attrs and attrs["examination"] != self.instance.examination:
            raise serializers.ValidationError({"examination_id": "Create a new preparation profile to change examination."})
        return attrs
