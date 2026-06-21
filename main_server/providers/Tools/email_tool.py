from __future__ import annotations

import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from main_server.core.audit import audit_log
from main_server.core.logger import logger
from main_server.services.runtime_settings import runtime_settings


class EmailProvider:
    """SMTP 邮件发送；未配置 SMTP 或 dry_run 时仅记录日志。"""

    def send(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict:
        settings = runtime_settings.get_email_settings()
        to = to.strip()
        if not to or "@" not in to:
            return {"sent": False, "error": "invalid_recipient", "to": to}

        if not settings.enabled:
            return {"sent": False, "error": "email_disabled"}

        if settings.dry_run or not settings.smtp_host:
            message_id = f"dry-{uuid.uuid4().hex[:12]}"
            logger.info(
                "email.dry_run to=%s subject=%s body_len=%s message_id=%s",
                to,
                subject,
                len(body),
                message_id,
            )
            audit_log(
                "email.dry_run",
                resource=f"email:{to}",
                detail=f"subject={subject} message_id={message_id}",
            )
            return {
                "sent": True,
                "dry_run": True,
                "message_id": message_id,
                "to": to,
                "subject": subject,
            }

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.from_address
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.use_tls:
                    smtp.starttls()
                if settings.smtp_user and settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        except Exception as exc:
            logger.exception("email.send_failed to=%s", to)
            return {"sent": False, "error": str(exc), "to": to}

        message_id = uuid.uuid4().hex
        logger.info("email.sent to=%s subject=%s message_id=%s", to, subject, message_id)
        audit_log(
            "email.sent",
            resource=f"email:{to}",
            detail=f"subject={subject} message_id={message_id}",
        )
        return {
            "sent": True,
            "dry_run": False,
            "message_id": message_id,
            "to": to,
            "subject": subject,
        }


_email_provider: EmailProvider | None = None


def get_email_provider() -> EmailProvider:
    global _email_provider
    if _email_provider is None:
        _email_provider = EmailProvider()
    return _email_provider
