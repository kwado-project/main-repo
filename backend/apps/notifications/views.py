from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Notification


@api_view(["GET"])
def list_notifications(request):
    qs = Notification.objects.filter(user=request.user)[:30]
    unread = Notification.objects.filter(user=request.user, read_at__isnull=True).count()
    return Response({"unread": unread, "items": [
        {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link, "read": bool(n.read_at),
         "created_at": n.created_at} for n in qs]})


@api_view(["POST"])
def mark_read(request):
    qs = Notification.objects.filter(user=request.user, read_at__isnull=True)
    if ids := request.data.get("ids"):
        qs = qs.filter(id__in=ids)
    qs.update(read_at=timezone.now())
    return Response(status=204)
