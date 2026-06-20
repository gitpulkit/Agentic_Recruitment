import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List


def is_smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def _smtp_settings() -> Dict[str, str]:
    host = os.getenv("SMTP_HOST", "")
    port = os.getenv("SMTP_PORT", "587")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}

    if not host or not from_addr:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST and SMTP_FROM in .env"
        )

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from_addr": from_addr,
        "use_tls": use_tls,
    }


def send_outreach_email(to_email: str, subject: str, body: str) -> None:
    settings = _smtp_settings()
    message = MIMEMultipart()
    message["From"] = settings["from_addr"]
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings["host"], int(settings["port"]), timeout=30) as server:
        if settings["use_tls"]:
            server.starttls()
        if settings["user"] and settings["password"]:
            server.login(settings["user"], settings["password"])
        server.sendmail(settings["from_addr"], [to_email], message.as_string())


def send_campaign_emails(
    drafts: List[Dict[str, str]], recipient_emails: Dict[str, str]
) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []

    for draft in drafts:
        username = draft["username"]
        to_email = (recipient_emails.get(username) or "").strip()
        if not to_email:
            results.append(
                {
                    "username": username,
                    "status": "skipped",
                    "detail": "No email address provided",
                }
            )
            continue

        try:
            send_outreach_email(
                to_email=to_email,
                subject=draft.get("subject") or "Opportunity",
                body=draft.get("body") or "",
            )
            results.append(
                {
                    "username": username,
                    "email": to_email,
                    "status": "sent",
                    "detail": "Email sent successfully",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "username": username,
                    "email": to_email,
                    "status": "failed",
                    "detail": str(exc),
                }
            )

    return results
