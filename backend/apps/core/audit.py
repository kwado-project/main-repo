from .models import AuditLog


def client_ip(request):
    if request is None:
        return None
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(action, *, actor=None, target=None, request=None, **metadata):
    AuditLog.objects.create(
        actor=actor if (actor is not None and getattr(actor, "pk", None)) else None,
        action=action,
        target_type=target.__class__.__name__ if target is not None else "",
        target_id=str(getattr(target, "pk", "")) if target is not None else "",
        ip_address=client_ip(request),
        metadata=metadata,
    )
