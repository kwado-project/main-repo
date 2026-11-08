import uuid


class RequestIdMiddleware:
    """Attach a request id to every request/response for log correlation."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        request.request_id = rid
        response = self.get_response(request)
        response["X-Request-Id"] = rid
        return response
