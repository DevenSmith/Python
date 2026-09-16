"""SMTP delivery for account verification and password-reset messages."""

import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from tinyrpg.config import settings


def send_email(recipient: str, subject: str, body: str) -> None:
    if not settings.email_delivery_enabled or settings.smtp_host is None:
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.use_smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username is not None and settings.smtp_password is not None:
            smtp.login(
                settings.smtp_username,
                settings.smtp_password.get_secret_value(),
            )
        smtp.send_message(message)


def send_verification_email(recipient: str, token: str) -> None:
    link = f"{settings.frontend_url.rstrip('/')}?verify_token={quote(token)}"
    send_email(
        recipient,
        "Verify your Tiny RPG email",
        "Welcome to Tiny RPG. Verify your email by opening this link:\n\n"
        f"{link}\n\nThis link expires in {settings.verification_token_expire_hours} hours.",
    )


def send_password_reset_email(recipient: str, token: str) -> None:
    link = f"{settings.frontend_url.rstrip('/')}?reset_token={quote(token)}"
    send_email(
        recipient,
        "Reset your Tiny RPG password",
        "A password reset was requested for your Tiny RPG account. Open this link:\n\n"
        f"{link}\n\nThis link expires in {settings.password_reset_token_expire_minutes} minutes. "
        "Ignore this message if you did not request a reset.",
    )
