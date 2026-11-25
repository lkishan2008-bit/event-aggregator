"""Sending emails.

Order of preference:
1. Gmail SMTP (GMAIL_USER + GMAIL_APP_PASSWORD in .env) - sends to any address.
2. Amazon SES (SES_SENDER + AWS keys in .env).
3. Nothing configured (local development) - the email is printed in the terminal.

If sending fails, the email is printed in the terminal instead, so signup never crashes.
"""
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from flask import current_app


def _print_email(to, subject, text, note=""):
    label = "[DEV EMAIL]" if not note else f"[EMAIL NOT SENT: {note}]"
    print(f"\n{label} to={to}\nSubject: {subject}\n{text}\n", flush=True)


def _send_gmail(user, password, to, subject, text):
    msg = EmailMessage()
    msg["From"] = formataddr(("Event Aggregator", user))
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(user, password)
        server.send_message(msg)


def _send_ses(sender, region, to, subject, text):
    import boto3  # imported here so local dev works without AWS set up

    client = boto3.client("ses", region_name=region)
    client.send_email(
        Source=sender,
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": text, "Charset": "UTF-8"}},
        },
    )


def send_email(to, subject, text):
    app = current_app

    # tests: keep emails in memory so tests can read the code
    if app.config.get("TESTING"):
        app.extensions.setdefault("outbox", []).append({"to": to, "subject": subject, "text": text})
        return

    gmail_user = app.config.get("GMAIL_USER")
    gmail_password = app.config.get("GMAIL_APP_PASSWORD")
    ses_sender = app.config.get("SES_SENDER")

    try:
        if gmail_user and gmail_password:
            _send_gmail(gmail_user, gmail_password, to, subject, text)
            print(f"[EMAIL SENT via Gmail] to={to} subject={subject}", flush=True)
        elif ses_sender:
            _send_ses(ses_sender, app.config["AWS_REGION"], to, subject, text)
            print(f"[EMAIL SENT via SES] to={to} subject={subject}", flush=True)
        else:
            _print_email(to, subject, text)
    except Exception as exc:  # never let an email problem break signup or login
        app.logger.warning("Email to %s failed: %s", to, exc)
        _print_email(to, subject, text, note=type(exc).__name__)