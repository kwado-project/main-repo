import secrets
import string

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel

REFERRAL_ALPHABET = string.ascii_uppercase.replace("O", "").replace("I", "") + "23456789"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def canonical_email(email: str) -> str:
    """Canonical form for abuse detection (gmail dots / +tags collapse)."""
    email = normalize_email(email)
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    local = local.split("+", 1)[0]
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def generate_referral_code() -> str:
    return "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(8))


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, **extra):
        email = normalize_email(email)
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=email, canonical_email=canonical_email(email), **extra)
        user.set_unusable_password()  # passwordless: OTP only
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", User.Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        user = self.create_user(email, **extra)
        if password:  # Django admin site only; the product itself is OTP-only.
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        CONTENT_MANAGER = "content_manager", "Content manager"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    canonical_email = models.CharField(max_length=254, db_index=True)
    full_name = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)
    referral_code = models.CharField(max_length=12, unique=True, default=generate_referral_code)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    signup_bonus_granted = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def first_name(self):
        return (self.full_name or self.email.split("@")[0]).split(" ")[0]


class StudentProfile(TimeStampedModel):
    class LeaderboardVisibility(models.TextChoices):
        PUBLIC = "public", "Show my display name"
        ANONYMOUS = "anonymous", "Show as anonymous"
        HIDDEN = "hidden", "Hide me from leaderboards"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=40, blank=True)
    avatar_key = models.CharField(max_length=255, blank=True)
    avatar_color = models.CharField(max_length=9, default="#16A34A")
    state = models.CharField(max_length=60, blank=True)
    school = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    study_goal = models.CharField(max_length=255, blank=True)
    daily_goal_minutes = models.PositiveSmallIntegerField(default=30)
    leaderboard_visibility = models.CharField(
        max_length=12, choices=LeaderboardVisibility.choices, default=LeaderboardVisibility.PUBLIC
    )
    notify_email_reminders = models.BooleanField(default=True)
    notify_streak = models.BooleanField(default=True)
    notify_product = models.BooleanField(default=False)
    total_xp = models.PositiveIntegerField(default=0, db_index=True)
    level = models.PositiveSmallIntegerField(default=1)
    active_student_exam = models.ForeignKey(
        "examinations.StudentExam", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    onboarding_completed = models.BooleanField(default=False)
    tour_completed = models.BooleanField(default=False, help_text="Finished or skipped the first-visit app tour")

    def public_name(self):
        if self.leaderboard_visibility == self.LeaderboardVisibility.ANONYMOUS:
            return f"Learner #{self.user_id % 100000:05d}"
        return self.display_name or self.user.first_name


class EmailOTP(TimeStampedModel):
    class Purpose(models.TextChoices):
        REGISTER = "register", "Register"
        LOGIN = "login", "Login"

    email = models.EmailField(db_index=True)
    purpose = models.CharField(max_length=10, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)
    invalidated = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=12, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["email", "-created_at"])]

    @property
    def is_usable(self):
        return not self.consumed_at and not self.invalidated and self.expires_at > timezone.now()


class SignupBonusClaim(TimeStampedModel):
    """One signup bonus per canonical email, ever — survives account deletion."""

    canonical_email = models.CharField(max_length=254, unique=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
