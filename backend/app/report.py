"""Sponsor report: one page of real numbers per event, for organizers to show sponsors.

Everything comes from data we already have: registrations, verified payments and QR check-ins.
"""
from collections import Counter
from datetime import timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify

from .checkin import _own_event
from .events import serialize_event
from .models import Registration, User
from .utils import error, roles_required, to_iso_utc, utcnow_naive

bp = Blueprint("report", __name__, url_prefix="/api/organizer")

PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "rediffmail.com"}


def _institution(email):
    """Where an attendee comes from, judged by their email domain (rvce.edu.in -> rvce.edu.in)."""
    domain = email.split("@")[-1].lower()
    if domain in PERSONAL_DOMAINS:
        return "Personal email"
    return domain


def _local(dt, tz):
    return dt.replace(tzinfo=timezone.utc).astimezone(tz) if dt.tzinfo is None else dt.astimezone(tz)


@bp.get("/events/<int:event_id>/report")
@roles_required("organizer", "admin")
def sponsor_report(event_id):
    event = _own_event(event_id)
    if not event:
        return error("Event not found.", 404)
    tz = ZoneInfo(event.timezone)

    regs = Registration.query.filter_by(event_id=event.id).all()
    going = [r for r in regs if r.status == "registered"]
    arrived = [r for r in going if r.checked_in_at]
    paid = [r for r in going if (r.amount_paid or 0) > 0]
    users = {u.id: u for u in User.query.filter(User.id.in_([r.user_id for r in going] or [0])).all()}

    institutions = Counter(_institution(users[r.user_id].email) for r in going if r.user_id in users)
    cities = Counter((users[r.user_id].city or "Not given") for r in going if r.user_id in users)
    arrivals = Counter(_local(r.checked_in_at, tz).strftime("%H:00") for r in arrived)
    signups = Counter(_local(r.created_at, tz).strftime("%Y-%m-%d") for r in going)

    return jsonify({
        "event": serialize_event(event, len(going)),
        "generated_at": to_iso_utc(utcnow_naive()),
        "totals": {
            "registered": len(going),
            "checked_in": len(arrived),
            "attendance_rate": round(100 * len(arrived) / len(going)) if going else 0,
            "cancelled": sum(1 for r in regs if r.status == "cancelled"),
            "paid_tickets": len(paid),
            "revenue": float(sum((r.amount_paid or 0) for r in paid)),
            "currency": event.currency,
        },
        "institutions": [{"name": k, "count": v} for k, v in institutions.most_common(10)],
        "cities": [{"name": k, "count": v} for k, v in cities.most_common(10)],
        "arrivals_by_hour": [{"hour": k, "count": arrivals[k]} for k in sorted(arrivals)],
        "registrations_by_day": [{"day": k, "count": signups[k]} for k in sorted(signups)],
    })