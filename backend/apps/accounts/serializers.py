from rest_framework import serializers

from apps.examinations.serializers import StudentExamSerializer

from .models import StudentProfile, User


class OTPRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    intent = serializers.ChoiceField(choices=["register", "login"])
    referral_code = serializers.CharField(max_length=12, required=False, allow_blank=True)


class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    code = serializers.RegexField(r"^\d{6}$")
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = (
            "display_name", "avatar_color", "state", "school", "study_goal", "daily_goal_minutes",
            "leaderboard_visibility", "notify_email_reminders", "notify_streak", "notify_product",
            "total_xp", "level", "onboarding_completed", "active_student_exam",
        )
        read_only_fields = ("total_xp", "level", "onboarding_completed")

    def validate_active_student_exam(self, value):
        if value and value.user_id != self.context["request"].user.id:
            raise serializers.ValidationError("Not found.")
        return value


class MeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    balance = serializers.SerializerMethodField()
    student_exams = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role", "referral_code", "date_joined", "profile", "balance",
                  "student_exams")
        read_only_fields = ("id", "email", "role", "referral_code", "date_joined")

    def get_balance(self, obj):
        w = getattr(obj, "wallet", None)
        return w.balance if w else 0

    def get_student_exams(self, obj):
        qs = obj.student_exams.filter(is_archived=False).select_related("examination").prefetch_related("subjects")
        return StudentExamSerializer(qs, many=True).data

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        if "full_name" in validated_data:
            instance.full_name = validated_data["full_name"]
            instance.save(update_fields=["full_name"])
        if profile_data:
            for k, v in profile_data.items():
                setattr(instance.profile, k, v)
            instance.profile.save()
        return instance
