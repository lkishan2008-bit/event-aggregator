"""Saved tab: students bookmark events to find them again later."""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from .events import _going_counts, serialize_event
from .extensions import db
from .models import Event, SavedEvent
from .utils import error, utcnow_naive

bp = Blueprint("saved", __name__, url_prefix="/api")


@bp.post("/events/<int:event_id>/save")
@jwt_required()
def save(event_id):
    event = db.session.get(Event, event_id)
    if not event or event.status != "approved":
        return error("Event not found.", 404)
    user_id = int(get_jwt_identity())
    if not SavedEvent.query.filter_by(user_id=user_id, event_id=event_id).first():
        db.session.add(SavedEvent(user_id=user_id, event_id=event_id))
        db.session.commit()
    return jsonify({"saved": True})


@bp.delete("/events/<int:event_id>/save")
@jwt_required()
def unsave(event_id):
    SavedEvent.query.filter_by(user_id=int(get_jwt_identity()), event_id=event_id).delete()
    db.session.commit()
    return jsonify({"saved": False})


@bp.get("/me/saved")
@jwt_required()
def my_saved():
    """Saved events that are still live, soonest first (finished or removed events drop off)."""
    ids = [s.event_id for s in SavedEvent.query.filter_by(user_id=int(get_jwt_identity())).all()]
    now = utcnow_naive()
    events = [e for e in Event.query.filter(Event.id.in_(ids or [0]), Event.status == "approved").all()
              if (e.end_utc or e.start_utc) >= now]
    events.sort(key=lambda e: e.start_utc)
    counts = _going_counts([e.id for e in events])
    return jsonify({"events": [serialize_event(e, counts.get(e.id, 0)) for e in events], "ids": ids})