"""Trust & safety: stop fake or scam events before they reach students.

1. Verified organizers: prove you own an official college email (OTP sent to it).
2. Red flags: automatic checks on every event (pay-outside-the-app, duplicates, spam words...).
3. Reports: students can report an event; after REPORTS_TO_HIDE reports it is hidden for admin review.
Verified organizers with a clean (no red flags) event go live directly; everyone else waits for an admin.
"""
import re
from datetime import timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from .extensions import db
from .models import Event, EventReport, OrganizerVerification, User
from .otp import issue_otp, seconds_until_resend, verify_otp
from .utils import error, roles_required, to_iso_utc, utcnow_naive

bp = Blueprint("trust", __name__, url_prefix="/api")

REPORTS_TO_HIDE = 3
REPORT_REASONS = ("fake", "scam", "wrong_details", "spam", "other")
OFFICIAL_DOMAIN = re.compile(r"\.(edu|ac)(\.[a-z]{2})?$")       # rvce.edu.in, iisc.ac.in, mit.edu
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)

UPI_RE = re.compile(r"\b[\w.\-]{2,}@(?!gmail|yahoo|outlook|hotmail)[a-z]{2,}\b(?!\.[a-z])", re.I)   # name@okaxis (not name@site.com)
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b")
PAY_WORDS = re.compile(r"\b(gpay|google pay|phonepe|paytm|upi|send money|pay (?:to|on|at|via)|transfer)\b", re.I)
SPAM_WORDS = re.compile(r"\b(guaranteed|100% placement|limited seats only today|earn \S+ per day|work from home|crypto|investment plan|double your)\b", re.I)


# ---------- verification ----------

def verified_domain(user_id):
    v = OrganizerVerification.query.filter_by(user_id=user_id).first()
    return v.domain if v and v.verified_at else None


@bp.get("/organizer/verification")
@roles_required("organizer", "admin")
def verification_status():
    v = OrganizerVerification.query.filter_by(user_id=int(get_jwt_identity())).first()
    return jsonify({"verification": {
        "email": v.email, "verified": bool(v.verified_at), "verified_at": to_iso_utc(v.verified_at),
    } if v else None})


@bp.post("/organizer/verify/start")
@roles_required("organizer", "admin")
def verify_start():
    """Body: {"email": "club@rvce.edu.in"}. Sends a 6-digit code to that official email."""
    email = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    if not EMAIL_RE.match(email) or not OFFICIAL_DOMAIN.search(email.split("@")[-1]):
        return error("Use your official college email, e.g. name@rvce.edu.in or name@iisc.ac.in.")
    user = db.session.get(User, int(get_jwt_identity()))
    wait = seconds_until_resend(user, "org_verify")
    if wait:
        return error(f"Wait {wait} seconds before asking for a new code.", 429)

    v = OrganizerVerification.query.filter_by(user_id=user.id).first() or OrganizerVerification(user_id=user.id, email=email)
    if v.verified_at and v.email == email:
        return jsonify({"sent": False, "verified": True})
    v.email, v.verified_at = email, None
    db.session.add(v)
    db.session.commit()
    issue_otp(user, "org_verify", to=email)
    return jsonify({"sent": True, "email": email})


@bp.post("/organizer/verify/confirm")
@roles_required("organizer", "admin")
def verify_confirm():
    code = str((request.get_json(silent=True) or {}).get("code", "")).strip()
    user = db.session.get(User, int(get_jwt_identity()))
    v = OrganizerVerification.query.filter_by(user_id=user.id).first()
    if not v:
        return error("Start verification first.")
    problem = verify_otp(user, "org_verify", code)
    if problem:
        return error(problem)
    v.verified_at = utcnow_naive()
    db.session.commit()
    return jsonify({"verified": True, "email": v.email})


# ---------- red flags ----------

def red_flags(event):
    """Reasons an admin should look twice at this event (empty list = looks fine)."""
    flags = []
    text = f"{event.title}\n{event.description or ''}"
    if UPI_RE.search(text) or (PAY_WORDS.search(text) and PHONE_RE.search(text)):
        flags.append("Asks to pay outside the app (UPI ID or payment number)")
    elif PHONE_RE.search(text):
        flags.append("Phone number in the description")
    if SPAM_WORDS.search(text):
        flags.append("Spam-like promises in the text")
    if event.price_amount is not None and float(event.price_amount) > 5000:
        flags.append("Unusually high price")
    if event.start_utc and event.created_at:
        created = event.created_at.replace(tzinfo=None) if event.created_at.tzinfo else event.created_at
        if event.start_utc - created < timedelta(hours=6):
            flags.append("Starts less than 6 hours after it was posted")
    if event.id and event.start_utc:
        same = Event.query.filter(
            Event.id != event.id, func.lower(Event.title) == event.title.lower(),
            Event.status.in_(("pending", "approved")),
            Event.start_utc.between(event.start_utc - timedelta(hours=12), event.start_utc + timedelta(hours=12)),
        ).first()
        if same:
            flags.append("Looks like a duplicate of another event")
    if not verified_domain(event.organizer_id):
        flags.append("Organizer is not verified")
    return flags


def report_count(event_id):
    return EventReport.query.filter_by(event_id=event_id).count()


# ---------- reports ----------

@bp.post("/events/<int:event_id>/report")
@jwt_required()
def report_event(event_id):
    """Body: {"reason": "fake|scam|wrong_details|spam|other", "details": "..."}."""
    event = db.session.get(Event, event_id)
    if not event or event.status != "approved":
        return error("Event not found.", 404)
    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    if reason not in REPORT_REASONS:
        return error(f"reason must be one of: {', '.join(REPORT_REASONS)}.")
    user_id = int(get_jwt_identity())
    if event.organizer_id == user_id:
        return error("You can't report your own event.")
    if EventReport.query.filter_by(event_id=event_id, user_id=user_id).first():
        return jsonify({"reported": True, "already": True})

    db.session.add(EventReport(event_id=event_id, user_id=user_id, reason=reason, details=str(data.get("details") or "")[:500] or None))
    db.session.flush()
    hidden = False
    if report_count(event_id) >= REPORTS_TO_HIDE:
        event.status = "pending"   # taken out of the public feed until an admin decides
        hidden = True
    db.session.commit()
    return jsonify({"reported": True, "hidden": hidden})


@bp.get("/admin/events/<int:event_id>/reports")
@roles_required("admin")
def list_reports(event_id):
    reports = EventReport.query.filter_by(event_id=event_id).order_by(EventReport.created_at.desc()).all()
    return jsonify({"reports": [{"reason": r.reason, "details": r.details, "created_at": to_iso_utc(r.created_at)} for r in reports]})