from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class InsufficientCredits(APIException):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "You do not have enough credits for this activity."
    default_code = "insufficient_credits"


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "This service is temporarily unavailable. You have not been charged."
    default_code = "service_unavailable"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict) and "code" not in response.data:
        code = getattr(exc, "default_code", None) or getattr(getattr(exc, "detail", None), "code", None)
        if code:
            response.data["code"] = code
    return response
