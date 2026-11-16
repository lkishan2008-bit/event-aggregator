"""Sending emails.

If AWS SES is configured in .env (SES_SENDER + AWS keys), emails go out through Amazon SES.
Otherwise (local development) the email is printed in the backend terminal instead.
"""
from flask import current_app


def send_email(to, subject, text):
    app = current_app

    # tests: keep emails in memory so tests can read the code
    if app.config.get("TESTING"):
        app.extensions.setdefault("outbox", []).append({"to": to, "subject": subject, "text": text})
        return

    sender = app.config.get("SES_SENDER")
    if not sender:
        print(f"\n[DEV EMAIL] to={to}\nSubject: {subject}\n{text}\n", flush=True)
        return

    import boto3  # imported here so local dev works without AWS set up

    client = boto3.client("ses", region_name=app.config["AWS_REGION"])
    client.send_email(
        Source=sender,
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": text, "Charset": "UTF-8"}},
        },
    )