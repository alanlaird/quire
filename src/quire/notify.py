from __future__ import annotations

import smtplib
from email.message import EmailMessage

from quire.config import EmailConfig


def send(cfg: EmailConfig, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.from_addr
    msg["To"] = cfg.to
    msg.set_content(body)

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=30) as s:
        s.starttls()
        s.login(cfg.smtp_username, cfg.smtp_password)
        s.send_message(msg)
