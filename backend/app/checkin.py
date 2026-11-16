"""Gate check-in: the organizer scans a student's QR pass and the server marks it as used."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from .extensions import db
from .models import Event, Registration, User
from .utils import error, roles_required, to_iso_utc, utcnow_naive

bp = Blueprint("checkin", __name__, url_prefix="/api/organizer")


def _own_event(event_id):
    """The event if the logged-in user organizes it (admins can manage every event), else None."""
    event = db.session.get(Event, event_id)
    if not event:
        return None
    if get_jwt().get("role") != "admin" and event.organizer_id != int(get_jwt_identity()):
        return None
    return event


def _attendee(reg):
    user = db.session.get(User, reg.user_id)
    return {"registration_id": reg.id, "name": user.name, "email": user.email, "checked_in_at": to_iso_utc(reg.checked_in_at)}


@bp.post("/events/<int:event_id>/checkin")
@roles_required("organizer", "admin")
def check_in(event_id):
    """Body: {"code": "<text from the QR code>"}. Marks the pass as used, exactly once.

    Every scan answer (ok, already used, wrong event...) is a normal 200 reply with a "result" field,
    so the scanner screen can show green / amber / red.
    """
    event = _own_event(event_id)
    if not event:
        return error("Event not found.", 404)

    code = str((request.get_json(silent=True) or {}).get("code", "")).strip()
    if not code:
        return error("Scan a QR code or type the pass code.")

    reg = Registration.query.filter_by(qr_token=code).first()
    if not reg:
        return jsonify({"result": "invalid", "message": "Not a valid pass."})
    if reg.event_id != event.id:
        return jsonify({"result": "wrong_event", "message": "This pass is for a different event."})
    if reg.status != "registered":
        return jsonify({"result": "cancelled", "message": "This registration was cancelled.", "attendee": _attendee(reg)})
    if reg.checked_in_at:
        return jsonify({"result": "already", "message": "Already checked in.", "attendee": _attendee(reg)})

    reg.checked_in_at = utcnow_naive()
    db.session.commit()
    return jsonify({"result": "ok", "message": "Checked in.", "attendee": _attendee(reg)})


@bp.get("/events/<int:event_id>/checkins")
@roles_required("organizer", "admin")
def stats(event_id):
    """Live numbers for the scanner screen: going, checked in, and the latest arrivals."""
    event = _own_event(event_id)
    if not event:
        return error("Event not found.", 404)
    regs = Registration.query.filter_by(event_id=event.id, status="registered").all()
    arrived = sorted((r for r in regs if r.checked_in_at), key=lambda r: r.checked_in_at, reverse=True)
    return jsonify({
        "event": {"id": event.id, "title": event.title},
        "going": len(regs),
        "checked_in": len(arrived),
        "recent": [_attendee(r) for r in arrived[:10]],
    })