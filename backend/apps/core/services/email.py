"""Transactional email.

Providers (EMAIL_PROVIDER):
  * "smtp"    — any SMTP server; configured for Gmail with an App Password by default.
  * "ses"     — AWS SES (SESv2 API), for higher volumes.
  * "console" — development only: messages are logged, clearly marked, never sent.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection

logger = logging.getLogger("kwado.email")

_ses_client = None


def _ses():
    global _ses_client
    if _ses_client is None:
        import boto3

        kwargs = {"region_name": settings.AWS_SES_REGION}
        if settings.AWS_SES_ACCESS_KEY_ID:
            kwargs.update(
                aws_access_key_id=settings.AWS_SES_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SES_SECRET_ACCESS_KEY,
            )
        _ses_client = boto3.client("sesv2", **kwargs)
    return _ses_client


def _send_smtp(to: str, subject: str, text: str, html: str | None) -> None:
    connection = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=settings.EMAIL_USE_SSL,
        timeout=settings.EMAIL_TIMEOUT,
    )
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to], connection=connection)
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)  # raise so the Celery task retries


def _send_ses(to: str, subject: str, text: str, html: str | None) -> None:
    body = {"Text": {"Data": text, "Charset": "UTF-8"}}
    if html:
        body["Html"] = {"Data": html, "Charset": "UTF-8"}
    params = {
        "FromEmailAddress": settings.DEFAULT_FROM_EMAIL,
        "Destination": {"ToAddresses": [to]},
        "Content": {"Simple": {"Subject": {"Data": subject, "Charset": "UTF-8"}, "Body": body}},
    }
    if settings.AWS_SES_CONFIGURATION_SET:
        params["ConfigurationSetName"] = settings.AWS_SES_CONFIGURATION_SET
    _ses().send_email(**params)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    provider = settings.EMAIL_PROVIDER
    if provider == "smtp":
        _send_smtp(to, subject, text, html)
    elif provider == "ses":
        _send_ses(to, subject, text, html)
    else:
        # Development delivery — never used in production.
        logger.warning("[DEV EMAIL — not sent] to=%s subject=%s\n%s", to, subject, text)
