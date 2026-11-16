from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from .events import _going_counts, serialize_event
from .extensions import db
from .models import Event, Registration
from .utils import error, to_iso_utc, utcnow_naive

bp = Blueprint("registrations", __name__, url_prefix="/api")


def serialize_registration(reg, include_event=True):
    data = {
        "id": reg.id,
        "status": reg.status,
        "qr_token": reg.qr_token,
        "checked_in_at": to_iso_utc(reg.checked_in_at),
        "created_at": to_iso_utc(reg.created_at),
    }
    if include_event:
        event = db.session.get(Event, reg.event_id)
        data["event"] = serialize_event(event, _going_counts([event.id]).get(event.id, 0))
    return data


def _event_is_open(event):
    if not event or event.status != "approved":
        return False
    now = utcnow_naive()
    end = event.end_utc or event.start_utc
    return end >= now


@bp.post("/events/<int:event_id>/register")
@jwt_required()
def register(event_id):
    """Register the logged-in user for an event. Registering again after cancelling re-activates it."""
    event = db.session.get(Event, event_id)
    if not _event_is_open(event):
        return error("This event isn't open for registration.", 404 if not event else 400)

    user_id = int(get_jwt_identity())
    reg = Registration.query.filter_by(user_id=user_id, event_id=event_id).first()
    if reg and reg.status == "registered":
        return jsonify({"registration": serialize_registration(reg)})  # already going: same pass
    if reg:
        reg.status = "registered"
    else:
        reg = Registration(user_id=user_id, event_id=event_id)
        db.session.add(reg)
    db.session.commit()
    return jsonify({"registration": serialize_registration(reg)}), 201


@bp.delete("/events/<int:event_id>/register")
@jwt_required()
def cancel(event_id):
    reg = Registration.query.filter_by(user_id=int(get_jwt_identity()), event_id=event_id).first()
    if not reg or reg.status != "registered":
        return error("You're not registered for this event.", 404)
    if reg.checked_in_at:
        return error("You've already checked in, so this can't be cancelled.", 409)
    reg.status = "cancelled"
    db.session.commit()
    return jsonify({"registration": serialize_registration(reg)})


@bp.get("/events/<int:event_id>/my-registration")
@jwt_required()
def my_registration(event_id):
    reg = Registration.query.filter_by(user_id=int(get_jwt_identity()), event_id=event_id, status="registered").first()
    return jsonify({"registration": serialize_registration(reg, include_event=False) if reg else None})


@bp.get("/me/registrations")
@jwt_required()
def my_registrations():
    regs = Registration.query.filter_by(user_id=int(get_jwt_identity()), status="registered").all()
    items = [serialize_registration(r) for r in regs]
    items.sort(key=lambda r: r["event"]["start_utc"])
    return jsonify({"registrations": items})