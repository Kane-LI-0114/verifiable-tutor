"""Email delivery seam for verification codes and reset links.

The backend sends two messages: the registration code and the password reset
link. Delivery uses QQ Mail SMTP when the SMTP variables are configured, and
falls back to the backend log in development mode. The procedure and limits
are recorded in docs/email-local.md.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MimeMessage
from typing import Protocol

from ..settings import SmtpSettings

logger = logging.getLogger("verifiable_tutor.api.email")


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    """A boundary the tests replace; only delivery, never message content."""

    delivery: str

    def send(self, message: EmailMessage) -> None: ...


class DevLogEmailSender:
    """Development fallback: write the message to the backend log."""

    delivery = "log"

    def send(self, message: EmailMessage) -> None:
        logger.info(
            "email delivery disabled; message to %s, subject %r:\n%s",
            message.to,
            message.subject,
            message.body,
        )


class SmtpEmailSender:
    """SMTP delivery over implicit TLS or STARTTLS (QQ Mail)."""

    delivery = "smtp"

    def __init__(self, settings: SmtpSettings, *, timeout: float = 15.0) -> None:
        self._settings = settings
        self._timeout = timeout

    def send(self, message: EmailMessage) -> None:
        settings = self._settings
        sender = settings.sender or settings.user
        if not settings.host or not settings.user or not settings.password or not sender:
            raise RuntimeError("SMTP delivery is not fully configured")
        mime = MimeMessage()
        mime["To"] = message.to
        mime["From"] = sender
        mime["Subject"] = message.subject
        mime.set_content(message.body)
        if settings.security == "ssl":
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.host, settings.port, timeout=self._timeout
            )
        else:
            server = smtplib.SMTP(settings.host, settings.port, timeout=self._timeout)
            server.starttls()
        try:
            server.login(settings.user, settings.password)
            server.send_message(mime)
        finally:
            server.quit()


def build_email_sender(settings: SmtpSettings) -> EmailSender:
    """Pick SMTP when configured, otherwise the development log sender."""

    if settings.host and settings.user and settings.password:
        return SmtpEmailSender(settings)
    return DevLogEmailSender()
