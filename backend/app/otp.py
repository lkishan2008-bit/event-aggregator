import secrets
from datetime import timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from .email import send_email
from .extensions import db
from .models import OtpCode
from .utils import utcnow_naive

OTP_TTL = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5


def _latest(user, purpose):
    return (
        OtpCode.query.filter_by(user_id=user.id, purpose=purpose, used=False)
        .order_by(OtpCode.created_at.desc())
        .first()
    )


def seconds_until_resend(user, purpose):
    last = _latest(user, purpose)
    if not last:
        return 0
    wait = (last.created_at + RESEND_COOLDOWN - utcnow_naive()).total_seconds()
    return max(0, int(wait) + 1) if wait > 0 else 0


def issue_otp(user, purpose):
    """Create a new 6-digit code, invalidate older ones, and email it."""
    for old in OtpCode.query.filter_by(user_id=user.id, purpose=purpose, used=False):
        old.used = True

    code = f"{secrets.randbelow(1_000_000):06d}"
    now = utcnow_naive()
    db.session.add(OtpCode(
        user_id=user.id, purpose=purpose, code_hash=generate_password_hash(code),
        expires_at=now + OTP_TTL, created_at=now,
    ))
    db.session.commit()

    action = "finish creating your account" if purpose == "signup" else "log in"
    send_email(
        user.email,
        f"Your verification code: {code}",
        f"Hi {user.name},\n\nYour code to {action} is {code}.\n"
        f"It expires in 10 minutes. If you didn't try to {action}, you can ignore this email.",
    )


def verify_otp(user, purpose, code):
    """Return None if the code is correct, otherwise an error message."""
    otp = _latest(user, purpose)
    if not otp:
        return "No active code. Request a new one."
    if otp.expires_at < utcnow_naive():
        otp.used = True
        db.session.commit()
        return "This code has expired. Request a new one."
    if otp.attempts >= MAX_ATTEMPTS:
        return "Too many wrong attempts. Request a new code."

    if not check_password_hash(otp.code_hash, code):
        otp.attempts += 1
        db.session.commit()
        left = MAX_ATTEMPTS - otp.attempts
        return f"Wrong code. {left} attempt{'s' if left != 1 else ''} left." if left else "Too many wrong attempts. Request a new code."

    otp.used = True
    db.session.commit()
    return None