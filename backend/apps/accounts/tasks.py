from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.core.services.email import send_email

from .models import EmailOTP


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_otp_email(self, email: str, code: str, purpose: str):
    action = "create your Kwado AI account" if purpose == "register" else "sign in to Kwado AI"
    text = (
        f"Your Kwado AI verification code is {code}\n\n"
        f"Use it to {action}. It expires in 5 minutes and can only be used once.\n\n"
        "If you didn't request this, you can ignore this email. Kwado AI will never ask you for this code."
    )
    html = f"""<div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:auto;padding:24px">
<h2 style="color:#14532D;margin:0 0 8px">Kwado AI</h2>
<p style="color:#111827">Use this code to {action}:</p>
<p style="font-size:32px;letter-spacing:8px;font-weight:700;color:#16A34A;margin:16px 0">{code}</p>
<p style="color:#64748B;font-size:13px">Expires in 5 minutes. Single use. If you didn't request it, ignore this email.</p>
</div>"""
    send_email(email, f"{code} is your Kwado AI code", text, html, idempotency_key=f"otp/{self.request.id}")


@shared_task
def send_no_account_email(email: str):
    send_email(
        email, "Sign in attempt on Kwado AI",
        "Someone tried to sign in to Kwado AI with this email, but there's no account yet.\n"
        "Create one free at https://kwado.ai/register — new students get 100 free credits.",
    )


@shared_task
def purge_expired_otps():
    EmailOTP.objects.filter(created_at__lt=timezone.now() - timedelta(days=2)).delete()
