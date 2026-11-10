import os

for k, v in {"KWADO_TESTING": "1", "DJANGO_DEBUG": "1", "CELERY_TASK_ALWAYS_EAGER": "1", "EMAIL_PROVIDER": "console",
             "AI_PROVIDER": "dev_mock", "SECURE_SSL_REDIRECT": "0", "STORAGE_PROVIDER": "local"}.items():
    os.environ[k] = v
os.environ.pop("PAYSTACK_SECRET_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)

from .settings import *  # noqa: E402,F401,F403

LOCAL_STORAGE_ROOT = BASE_DIR / "var" / "test-uploads"  # noqa: F405
