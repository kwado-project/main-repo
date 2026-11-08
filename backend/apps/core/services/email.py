"""Transactional email via AWS SES (SESv2).

In development (`EMAIL_PROVIDER=console`) messages are logged instead of sent,
and the log line is clearly marked as a development delivery.
"""
import logging

from django.conf import settings

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


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    if settings.EMAIL_PROVIDER == "ses":
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
        return
    # Development delivery — never used in production.
    logger.warning("[DEV EMAIL — not sent] to=%s subject=%s\n%s", to, subject, text)
