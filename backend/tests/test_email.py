from unittest import mock

import pytest
from django.test import override_settings

from apps.core.services.email import send_email

GMAIL = dict(EMAIL_PROVIDER="smtp", EMAIL_HOST="smtp.gmail.com", EMAIL_PORT=587, EMAIL_HOST_USER="kwado@gmail.com",
             EMAIL_HOST_PASSWORD="abcdefghijklmnop", EMAIL_USE_TLS=True, EMAIL_USE_SSL=False,
             DEFAULT_FROM_EMAIL="Kwado AI <kwado@gmail.com>")


@override_settings(**GMAIL)
def test_smtp_gmail_starttls_login_and_multipart():
    with mock.patch("smtplib.SMTP") as smtp:
        conn = smtp.return_value
        conn.sendmail.return_value = {}
        send_email("student@example.com", "123456 is your Kwado AI code", "plain body", "<b>html body</b>")
    assert smtp.call_args.args[:2] == ("smtp.gmail.com", 587)
    conn.starttls.assert_called_once()
    conn.login.assert_called_once_with("kwado@gmail.com", "abcdefghijklmnop")
    frm, to, raw = conn.sendmail.call_args.args
    assert "kwado@gmail.com" in frm and to == ["student@example.com"]
    assert b"multipart/alternative" in raw and b"html body" in raw


@override_settings(**{**GMAIL, "EMAIL_PORT": 465, "EMAIL_USE_TLS": False, "EMAIL_USE_SSL": True})
def test_smtp_ssl_port_465():
    with mock.patch("smtplib.SMTP_SSL") as smtp:
        smtp.return_value.sendmail.return_value = {}
        send_email("s@example.com", "subj", "body")
    assert smtp.call_args.args[:2] == ("smtp.gmail.com", 465)


@override_settings(**GMAIL)
def test_smtp_failure_raises_so_celery_retries():
    import smtplib
    with mock.patch("smtplib.SMTP") as smtp:
        smtp.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Username and Password not accepted")
        with pytest.raises(smtplib.SMTPAuthenticationError):
            send_email("s@example.com", "subj", "body")


def test_app_password_spaces_are_stripped(monkeypatch):
    import importlib, config.test_settings as ts  # noqa: E401
    monkeypatch.setenv("EMAIL_HOST_PASSWORD", "abcd efgh ijkl mnop")
    import config.settings as s
    importlib.reload(s)
    assert s.EMAIL_HOST_PASSWORD == "abcdefghijklmnop"
    monkeypatch.delenv("EMAIL_HOST_PASSWORD")
    importlib.reload(s)


SES = dict(EMAIL_PROVIDER="ses", AWS_SES_REGION="eu-west-1", AWS_SES_ACCESS_KEY_ID="AKIATEST", AWS_SES_SECRET_ACCESS_KEY="secret",
           AWS_SES_CONFIGURATION_SET="kwado-tx", DEFAULT_FROM_EMAIL="Kwado AI <no-reply@kwado.example>")


@pytest.fixture
def fresh_ses_client(monkeypatch):
    import apps.core.services.email as em
    monkeypatch.setattr(em, "_ses_client", None)


@override_settings(**SES)
def test_ses_sends_html_and_text_with_configuration_set(fresh_ses_client):
    with mock.patch("boto3.client") as client:
        send_email("student@example.com", "123456 is your Kwado AI code", "plain", "<b>html</b>")
    assert client.call_args.args == ("sesv2",)
    assert client.call_args.kwargs == {"region_name": "eu-west-1", "aws_access_key_id": "AKIATEST", "aws_secret_access_key": "secret"}
    p = client.return_value.send_email.call_args.kwargs
    assert p["FromEmailAddress"] == "Kwado AI <no-reply@kwado.example>"
    assert p["Destination"] == {"ToAddresses": ["student@example.com"]}
    body = p["Content"]["Simple"]
    assert body["Subject"]["Data"] == "123456 is your Kwado AI code"
    assert body["Body"]["Text"]["Data"] == "plain" and body["Body"]["Html"]["Data"] == "<b>html</b>"
    assert p["ConfigurationSetName"] == "kwado-tx"


@override_settings(**{**SES, "AWS_SES_ACCESS_KEY_ID": None, "AWS_SES_SECRET_ACCESS_KEY": None})
def test_ses_without_keys_uses_default_aws_credential_chain(fresh_ses_client):
    with mock.patch("boto3.client") as client:
        send_email("s@example.com", "subj", "body")
    assert client.call_args.kwargs == {"region_name": "eu-west-1"}


@override_settings(**SES)
def test_ses_rejection_raises_so_celery_retries(fresh_ses_client):
    from botocore.exceptions import ClientError
    with mock.patch("boto3.client") as client:
        client.return_value.send_email.side_effect = ClientError(
            {"Error": {"Code": "MessageRejected", "Message": "Email address is not verified."}}, "SendEmail")
        with pytest.raises(ClientError):
            send_email("s@example.com", "subj", "body")


def test_ses_requires_verified_sender_in_production(monkeypatch):
    import importlib
    import config.settings as s
    for k, v in {"DJANGO_DEBUG": "0", "KWADO_TESTING": "1", "EMAIL_PROVIDER": "ses", "DEFAULT_FROM_EMAIL": ""}.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(RuntimeError, match="DEFAULT_FROM_EMAIL"):
        importlib.reload(s)
    monkeypatch.setenv("DEFAULT_FROM_EMAIL", "Kwado AI <no-reply@kwado.example>")
    importlib.reload(s)
    assert s.DEFAULT_FROM_EMAIL == "Kwado AI <no-reply@kwado.example>"
    for k in ("DJANGO_DEBUG", "EMAIL_PROVIDER", "DEFAULT_FROM_EMAIL"):
        monkeypatch.delenv(k)
    importlib.reload(s)
