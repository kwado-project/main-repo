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
  * Slow or external work (email via Resend, AI calls for document analysis,
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
    "apps.research",
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
    "apps.research.tasks.*": {"queue": "research"},
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
# Email — Resend (production) / console (development).
# AWS SES (EMAIL_PROVIDER=ses) and generic SMTP (EMAIL_PROVIDER=smtp) remain available.
# --------------------------------------------------------------------------
def env_secret(name):
    """Credential from env, tolerant of stray whitespace/quotes pasted into .env files."""
    v = (os.environ.get(name) or "").strip().strip("\"'").strip()
    return v or None


EMAIL_PROVIDER = env("EMAIL_PROVIDER", "console").strip().lower()  # "resend" | "ses" | "smtp" | "console"
RESEND_API_KEY = env_secret("RESEND_API_KEY")

AWS_SES_REGION = (env("AWS_SES_REGION") or "eu-west-1").strip()
# Leave the keys empty to use the standard AWS credential chain (e.g. an instance role).
AWS_SES_ACCESS_KEY_ID = env_secret("AWS_SES_ACCESS_KEY_ID")
AWS_SES_SECRET_ACCESS_KEY = env_secret("AWS_SES_SECRET_ACCESS_KEY")
AWS_SES_CONFIGURATION_SET = env("AWS_SES_CONFIGURATION_SET")

EMAIL_HOST = env("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = (env_secret("EMAIL_HOST_PASSWORD") or "").replace(" ", "")  # Gmail App Passwords are shown with spaces
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", EMAIL_PORT == 465)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", not EMAIL_USE_SSL)
EMAIL_TIMEOUT = int(env("EMAIL_TIMEOUT", "20"))

# Development only: echo OTP codes in the API response when no email provider is set.
OTP_DEV_ECHO = DEBUG and EMAIL_PROVIDER == "console"
# With Resend or SES this must be an address on a domain verified with that provider.
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL") or (f"Kwado AI <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "Kwado AI <no-reply@kwado.ai>")
if not DEBUG:
    if EMAIL_PROVIDER == "resend" and not (RESEND_API_KEY and env("DEFAULT_FROM_EMAIL")):
        raise RuntimeError("EMAIL_PROVIDER=resend needs RESEND_API_KEY and DEFAULT_FROM_EMAIL on a domain verified in Resend")
    if EMAIL_PROVIDER == "ses" and not env("DEFAULT_FROM_EMAIL"):
        raise RuntimeError("EMAIL_PROVIDER=ses needs DEFAULT_FROM_EMAIL on a domain verified in SES")
    if EMAIL_PROVIDER == "smtp" and not (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD):
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
# Provider selection: AI_PROVIDER forces "anthropic" | "openai" | "dev_mock". If unset,
# Anthropic is used when its key is present, otherwise OpenAI when its key is present,
# otherwise the clearly-labelled development mock.
ANTHROPIC_API_KEY = (env("ANTHROPIC_API_KEY") or "").strip() or None
OPENAI_API_KEY = (env("OPENAI_API_KEY") or "").strip() or None
AI_PROVIDER = (env("AI_PROVIDER") or "").strip().lower() or (
    "anthropic" if ANTHROPIC_API_KEY else "openai" if OPENAI_API_KEY else "dev_mock")
if AI_PROVIDER not in ("anthropic", "openai", "dev_mock"):
    raise RuntimeError("AI_PROVIDER must be anthropic, openai or dev_mock")
if AI_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY or AI_PROVIDER == "openai" and not OPENAI_API_KEY:
    raise RuntimeError(f"AI_PROVIDER={AI_PROVIDER} but its API key is not set")
AI_ANTHROPIC_MODEL = env("AI_ANTHROPIC_MODEL") or env("AI_DEFAULT_MODEL") or "claude-opus-5-5"
AI_OPENAI_MODEL = env("AI_OPENAI_MODEL") or "gpt-5.5"
AI_DEFAULT_MODEL = AI_OPENAI_MODEL if AI_PROVIDER == "openai" else AI_ANTHROPIC_MODEL
AI_MAX_OUTPUT_TOKENS = int(env("AI_MAX_OUTPUT_TOKENS", "4000"))
EMBEDDING_DIMENSIONS = 1024

# --------------------------------------------------------------------------
# Business rules
# --------------------------------------------------------------------------
SIGNUP_BONUS_CREDITS = 100
NAIRA_PER_CREDIT = 10
# Students may buy any whole number of credits in this range (price = credits × ₦10).
CUSTOM_CREDITS_MIN = int(env("CUSTOM_CREDITS_MIN", "50"))
CUSTOM_CREDITS_MAX = int(env("CUSTOM_CREDITS_MAX", "100000"))
REFERRAL_REWARD_PERCENT = 20
OTP_TTL_SECONDS = 300
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5

# --------------------------------------------------------------------------
# Past-question research pipeline (apps.research)
# --------------------------------------------------------------------------
# Honest, contactable User-Agent so site owners can identify and reach us.
RESEARCH_USER_AGENT = env("RESEARCH_USER_AGENT", "KwadoResearchBot/1.0 (+https://kwado.com.ng/research-bot)")
RESEARCH_YEAR_FROM = int(env("RESEARCH_YEAR_FROM", "2000"))
RESEARCH_YEAR_TO = int(env("RESEARCH_YEAR_TO", "2026"))
RESEARCH_DEFAULT_CRAWL_DELAY = float(env("RESEARCH_DEFAULT_CRAWL_DELAY", "5"))
RESEARCH_MAX_CRAWL_DEPTH = int(env("RESEARCH_MAX_CRAWL_DEPTH", "2"))
RESEARCH_MAX_PAGES_PER_SOURCE = int(env("RESEARCH_MAX_PAGES_PER_SOURCE", "300"))
RESEARCH_SEARCH_RESULTS_PER_QUERY = int(env("RESEARCH_SEARCH_RESULTS_PER_QUERY", "10"))
RESEARCH_SEARCH_AGAIN_AFTER_DAYS = int(env("RESEARCH_SEARCH_AGAIN_AFTER_DAYS", "14"))
RESEARCH_MAX_SEARCH_ATTEMPTS = int(env("RESEARCH_MAX_SEARCH_ATTEMPTS", "4"))
RESEARCH_TARGETS_PER_CYCLE = int(env("RESEARCH_TARGETS_PER_CYCLE", "20"))
RESEARCH_AUTORUN = env_bool("RESEARCH_AUTORUN", False)  # hourly autonomous cycle via Celery beat
RESEARCH_AI_REVIEW = env_bool("RESEARCH_AI_REVIEW", False)  # advisory AI answer check (costs AI credits)
RESEARCH_USE_PLAYWRIGHT = env_bool("RESEARCH_USE_PLAYWRIGHT", False)
# Search providers: every one with a key is used. Search-engine result pages are never scraped.
BRAVE_SEARCH_API_KEY = (env("BRAVE_SEARCH_API_KEY") or "").strip() or None
GOOGLE_CSE_API_KEY = (env("GOOGLE_CSE_API_KEY") or "").strip() or None
GOOGLE_CSE_CX = (env("GOOGLE_CSE_CX") or "").strip() or None
SERPAPI_API_KEY = (env("SERPAPI_API_KEY") or "").strip() or None
FIRECRAWL_API_KEY = (env("FIRECRAWL_API_KEY") or "").strip() or None

# --------------------------------------------------------------------------
# Opt in to the Django 6 default: URL form fields assume https:// when no scheme is typed.
FORMS_URLFIELD_ASSUME_HTTPS = True

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
