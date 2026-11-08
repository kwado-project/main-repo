from django.conf import settings


def read_db():
    """Database alias to use for read-heavy, eventually-consistent queries."""
    return "replica" if "replica" in settings.DATABASES else "default"
