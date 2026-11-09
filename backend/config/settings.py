"""
Kwado AI — Django settings.

All secrets and environment-specific values are read from environment
variables (see `.env.example`). Nothing secret is committed to the repo.

Scaling notes (target: 1M+ students):
  * The API is stateless (JWT access tokens + httpOnly refresh cookie), so any
    number of gunicorn/uvicorn workers can run behind a load balancer.
  * PostgreSQL is the system of record. Persistent connections are enabled and
    an optional read replica (`DATABASE_REPLICA_URL`) receives read traffic for
    read-heavy, non-critical endpoints (leaderboards, catalogue, analytics).
    Run PgBouncer in transaction mode in front of Postgres in production.
  * Redis backs the cache, throttling counters, leaderboards (sorted sets) and
    the Celery broker.
  * Slow or external work (email via SMTP/Gmail, AI calls for document analysis,
    roadmap generation, Paystack webhook post-processing) is done by Celery.
  * Uploaded files live in Cloudflare R2 (S3-compatible) and are only ever
    served through short-lived presigned URLs.
"""

from datetime import timedelta
from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [x.strip() for x in os.environ.get(name, default).split(",") if x.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG or env_bool("KWADO_TESTING"):
        SECRET_KEY = "dev-insecure-key-do-not-use-in-production"
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set in production")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3000")
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:3000")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    # Kwado modular monolith
    "apps.core",
    "apps.accounts",
    "apps.examinations",
    "apps.questions",
    "apps.assessments",
    "apps.learning",
    "apps.gamification",
    "apps.wallet",
    "apps.payments",
    "apps.referrals",
    "apps.ai_tutor",
    "apps.roadmaps",
    "apps.materials",
    "apps.notifications",
    "apps.analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", "postgres://kwado:kwado@localhost:5432/kwado"),
        conn_max_age=int(env("DB_CONN_MAX_AGE", "60")),
        conn_health_checks=True,
    )
}
if env("DATABASE_REPLICA_URL"):
    DATABASES["replica"] = dj_database_url.parse(
        env("DATABASE_REPLICA_URL"), conn_max_age=60, conn_health_checks=True
    )
    DATABASE_ROUTERS = ["apps.core.db_router.PrimaryReplicaRouter"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# --------------------------------------------------------------------------
# Cache / Redis
# --------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
if env_bool("KWADO_TESTING"):
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "kwado",
        }
    }

# --------------------------------------------------------------------------
# Celery
# --------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", DEBUG)
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ROUTES = {
    "apps.notifications.tasks.*": {"queue": "email"},
    "apps.materials.tasks.*": {"queue": "ai"},
    "apps.roadmaps.tasks.*": {"queue": "ai"},
}

# --------------------------------------------------------------------------
# REST framework
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", "60/min"),
        "user": env("THROTTLE_USER", "240/min"),
        "otp_request": env("THROTTLE_OTP_REQUEST", "5/10m"),
        "otp_verify": env("THROTTLE_OTP_VERIFY", "10/10m"),
        "ai": env("THROTTLE_AI", "20/min"),
        "payments": env("THROTTLE_PAYMENTS", "10/min"),
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(env("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(env("JWT_REFRESH_DAYS", "30"))),
    "ROTATE_REFRESH_TOKENS": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "SIGNING_KEY": env("JWT_SIGNING_KEY", SECRET_KEY),
}
REFRESH_COOKIE_NAME = "kwado_refresh"
REFRESH_COOKIE_SECURE = env_bool("REFRESH_COOKIE_SECURE", not DEBUG)
REFRESH_COOKIE_SAMESITE = env("REFRESH_COOKIE_SAMESITE", "Lax")

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True

# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --------------------------------------------------------------------------
# Email — SMTP, e.g. Gmail with an app password (production) / console (development)
# AWS SES remains available with EMAIL_PROVIDER=ses.
# --------------------------------------------------------------------------
EMAIL_PROVIDER = env("EMAIL_PROVIDER", "console")  # "smtp" | "ses" | "console"
EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
# Gmail: a 16-character App Password (Google Account → Security → 2-Step Verification → App passwords),
# never the normal account password. Spaces Google shows in it are ignored.
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "").replace(" ", "")
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", EMAIL_PORT == 465)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", not EMAIL_USE_SSL)
EMAIL_TIMEOUT = int(env("EMAIL_TIMEOUT", "20"))
AWS_SES_REGION = env("AWS_SES_REGION", "eu-west-1")
AWS_SES_ACCESS_KEY_ID = env("AWS_SES_ACCESS_KEY_ID")
AWS_SES_SECRET_ACCESS_KEY = env("AWS_SES_SECRET_ACCESS_KEY")
AWS_SES_CONFIGURATION_SET = env("AWS_SES_CONFIGURATION_SET")
# Development only: echo OTP codes in the API response when no email provider is set.
OTP_DEV_ECHO = DEBUG and EMAIL_PROVIDER == "console"
# Gmail rewrites the From address to the authenticated account unless it's a verified "Send mail as" alias.
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", f"Kwado AI <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "Kwado AI <no-reply@kwado.ai>")
if EMAIL_PROVIDER == "smtp" and not (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD) and not DEBUG:
    raise RuntimeError("EMAIL_PROVIDER=smtp needs EMAIL_HOST_USER and EMAIL_HOST_PASSWORD")

# --------------------------------------------------------------------------
# Object storage — Cloudflare R2 (production) / local disk (development)
# --------------------------------------------------------------------------
STORAGE_PROVIDER = env("STORAGE_PROVIDER", "local")  # "r2" | "local"
R2_ACCOUNT_ID = env("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY")
R2_BUCKET = env("R2_BUCKET", "kwado-materials")
R2_PRESIGN_SECONDS = int(env("R2_PRESIGN_SECONDS", "600"))
LOCAL_STORAGE_ROOT = BASE_DIR / "var" / "uploads"
MAX_UPLOAD_BYTES = int(env("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))

# --------------------------------------------------------------------------
# Payments — Paystack
# --------------------------------------------------------------------------
PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = env("PAYSTACK_PUBLIC_KEY")
PAYSTACK_BASE_URL = env("PAYSTACK_BASE_URL", "https://api.paystack.co")
# The dev sandbox provider only exists when DEBUG is on AND no Paystack key is
# configured. It never runs in production.
PAYMENTS_DEV_SANDBOX = DEBUG and not PAYSTACK_SECRET_KEY

# --------------------------------------------------------------------------
# AI — Anthropic Claude
# --------------------------------------------------------------------------
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
AI_PROVIDER = env("AI_PROVIDER", "anthropic" if ANTHROPIC_API_KEY else "dev_mock")
AI_DEFAULT_MODEL = env("AI_DEFAULT_MODEL", "claude-opus-5-5")
AI_MAX_OUTPUT_TOKENS = int(env("AI_MAX_OUTPUT_TOKENS", "4000"))
EMBEDDING_DIMENSIONS = 1024

# --------------------------------------------------------------------------
# Business rules
# --------------------------------------------------------------------------
SIGNUP_BONUS_CREDITS = 100
NAIRA_PER_CREDIT = 10
REFERRAL_REWARD_PERCENT = 20
OTP_TTL_SECONDS = 300
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5

# --------------------------------------------------------------------------
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
