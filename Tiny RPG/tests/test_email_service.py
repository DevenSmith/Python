from email.message import EmailMessage
from typing import Self

from pytest import MonkeyPatch

from tinyrpg.config import settings
from tinyrpg.email_service import send_password_reset_email, send_verification_email


class FakeSmtp:
    def __init__(self) -> None:
        self.messages: list[EmailMessage] = []
        self.started_tls = False
        self.credentials: tuple[str, str] | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self, context: object) -> None:
        self.started_tls = True

    def login(self, username: str, password: str) -> None:
        self.credentials = (username, password)

    def send_message(self, message: EmailMessage) -> None:
        self.messages.append(message)


def configure_fake_smtp(monkeypatch: MonkeyPatch) -> FakeSmtp:
    smtp = FakeSmtp()
    monkeypatch.setattr(settings, "email_delivery_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr(settings, "frontend_url", "https://game.example")
    monkeypatch.setattr(
        "tinyrpg.email_service.smtplib.SMTP",
        lambda host, port, timeout: smtp,
    )
    return smtp


def test_verification_email_contains_frontend_link(monkeypatch: MonkeyPatch) -> None:
    smtp = configure_fake_smtp(monkeypatch)

    send_verification_email("player@example.com", "token with spaces")

    assert len(smtp.messages) == 1
    message = smtp.messages[0]
    assert message["To"] == "player@example.com"
    assert message["Subject"] == "Verify your Tiny RPG email"
    assert "https://game.example?verify_token=token%20with%20spaces" in message.get_content()
    assert smtp.started_tls is True


def test_password_reset_email_contains_frontend_link(monkeypatch: MonkeyPatch) -> None:
    smtp = configure_fake_smtp(monkeypatch)

    send_password_reset_email("player@example.com", "reset-token")

    assert "https://game.example?reset_token=reset-token" in smtp.messages[0].get_content()
