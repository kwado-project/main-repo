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
