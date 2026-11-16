from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import func, or_

from .extensions import db
from .models import Event, Registration, Venue
from .trust import red_flags, report_count, verified_domain
from .utils import error, parse_utc, roles_required, to_iso_utc, utcnow_naive, valid_timezone

bp = Blueprint("events", __name__, url_prefix="/api")

CATEGORIES = ("fest", "hackathon", "workshop", "meetup", "conference", "cultural", "sports", "other")


def serialize_event(event, going=None):
    v = event.venue
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "start_utc": to_iso_utc(event.start_utc),
        "end_utc": to_iso_utc(event.end_utc),
        "timezone": event.timezone,
        "price_amount": float(event.price_amount or 0),
        "currency": event.currency,
        "is_free": bool(event.is_free),
        "poster_url": event.poster_url,
        "registration_url": event.registration_url,
        "status": event.status,
        "organizer": {
            "id": event.organizer.id, "name": event.organizer.name,
            "verified_domain": verified_domain(event.organizer.id),
        } if event.organizer else None,
        "venue": {
            "name": v.name, "address": v.address, "city": v.city, "country_code": v.country_code,
            "latitude": v.latitude, "longitude": v.longitude,
        } if v else None,
        "going": going if going is not None else 0,
        "updated_at": to_iso_utc(event.updated_at),
    }


def _going_counts(event_ids):
    if not event_ids:
        return {}
    rows = (
        db.session.query(Registration.event_id, func.count(Registration.id))
        .filter(Registration.event_id.in_(event_ids), Registration.status == "registered")
        .group_by(Registration.event_id)
        .all()
    )
    return dict(rows)


# ---------- public ----------

@bp.get("/events")
def list_events():
    """Approved, upcoming events. Filters: category, free=1, city, country, q, from, to, limit, offset."""
    args = request.args
    query = Event.query.outerjoin(Venue).filter(Event.status == "approved")

    # upcoming = not finished yet
    now = utcnow_naive()
    query = query.filter(or_(Event.end_utc >= now, (Event.end_utc.is_(None)) & (Event.start_utc >= now)))

    if args.get("category"):
        query = query.filter(Event.category == args["category"])
    if args.get("free") in ("1", "true"):
        query = query.filter(Event.is_free.is_(True))
    if args.get("city"):
        query = query.filter(func.lower(Venue.city) == args["city"].strip().lower())
    if args.get("country"):
        query = query.filter(Venue.country_code == args["country"].strip().upper())
    if args.get("q"):
        like = f"%{args['q'].strip().lower()}%"
        query = query.filter(or_(func.lower(Event.title).like(like), func.lower(Venue.name).like(like)))
    if args.get("from"):
        start = parse_utc(args["from"])
        if start is None:
            return error("'from' must be an ISO datetime with timezone.")
        query = query.filter(Event.start_utc >= start)
    if args.get("to"):
        end = parse_utc(args["to"])
        if end is None:
            return error("'to' must be an ISO datetime with timezone.")
        query = query.filter(Event.start_utc <= end)

    limit = min(max(args.get("limit", 50, type=int), 1), 100)
    offset = max(args.get("offset", 0, type=int), 0)

    total = query.count()
    events = query.order_by(Event.start_utc.asc()).offset(offset).limit(limit).all()
    counts = _going_counts([e.id for e in events])
    return jsonify({
        "events": [serialize_event(e, counts.get(e.id, 0)) for e in events],
        "total": total, "limit": limit, "offset": offset,
    })


@bp.get("/events/<int:event_id>")
def get_event(event_id):
    event = db.session.get(Event, event_id)
    if not event:
        return error("Event not found.", 404)

    if event.status != "approved":
        # only the organizer who owns it, or an admin, can see unapproved events
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        role = get_jwt().get("role") if identity else None
        if not identity or (role != "admin" and int(identity) != event.organizer_id):
            return error("Event not found.", 404)

    return jsonify({"event": serialize_event(event, _going_counts([event.id]).get(event.id, 0))})


# ---------- organizer ----------

@bp.post("/events")
@roles_required("organizer", "admin")
def create_event():
    data = request.get_json(silent=True) or {}

    title = (data.get("title") or "").strip()
    category = data.get("category")
    start = parse_utc(data.get("start_utc"))
    end = parse_utc(data.get("end_utc")) if data.get("end_utc") else None
    tz = data.get("timezone")
    venue_data = data.get("venue") or {}

    if not title:
        return error("Enter an event title.")
    if category not in CATEGORIES:
        return error(f"Category must be one of: {', '.join(CATEGORIES)}.")
    if start is None:
        return error("start_utc must be an ISO datetime with timezone, e.g. 2026-11-22T09:00:00+05:30.")
    if data.get("end_utc") and end is None:
        return error("end_utc must be an ISO datetime with timezone.")
    if end is not None and end < start:
        return error("The event can't end before it starts.")
    if start < utcnow_naive():
        return error("The event start time is in the past.")
    if not valid_timezone(tz):
        return error("timezone must be an IANA name, e.g. Asia/Kolkata.")

    try:
        price = Decimal(str(data.get("price_amount", 0)))
    except InvalidOperation:
        return error("price_amount must be a number.")
    if price < 0:
        return error("price_amount can't be negative.")
    currency = (data.get("currency") or "INR").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        return error("currency must be a 3-letter ISO code, e.g. INR or USD.")

    venue_name = (venue_data.get("name") or "").strip()
    city = (venue_data.get("city") or "").strip()
    country = (venue_data.get("country_code") or "").strip().upper()
    if not venue_name or not city or len(country) != 2:
        return error("venue needs name, city and a 2-letter country_code.")

    venue = Venue(
        name=venue_name, address=venue_data.get("address"), city=city, country_code=country,
        latitude=venue_data.get("latitude"), longitude=venue_data.get("longitude"),
    )
    role = get_jwt().get("role")
    event = Event(
        organizer_id=int(get_jwt_identity()),
        venue=venue,
        title=title,
        description=data.get("description"),
        category=category,
        start_utc=start,
        end_utc=end,
        timezone=tz,
        price_amount=price,
        currency=currency,
        is_free=(price == 0),
        poster_url=data.get("poster_url"),
        registration_url=data.get("registration_url"),
        source_url=data.get("source_url"),
        status="approved" if role == "admin" else "pending",
    )
    db.session.add(event)
    db.session.flush()
    # verified organizers skip the queue when the automatic checks find nothing suspicious
    if role != "admin" and verified_domain(event.organizer_id) and not red_flags(event):
        event.status = "approved"
    db.session.commit()
    return jsonify({"event": serialize_event(event)}), 201


@bp.get("/organizer/events")
@roles_required("organizer", "admin")
def my_events():
    events = (
        Event.query.filter_by(organizer_id=int(get_jwt_identity()))
        .order_by(Event.start_utc.desc()).all()
    )
    counts = _going_counts([e.id for e in events])
    return jsonify({"events": [serialize_event(e, counts.get(e.id, 0)) for e in events]})


# ---------- admin ----------

@bp.get("/admin/events")
@roles_required("admin")
def admin_list():
    status = request.args.get("status", "pending")
    if status not in Event.STATUSES:
        return error(f"status must be one of: {', '.join(Event.STATUSES)}.")
    events = Event.query.filter_by(status=status).order_by(Event.created_at.asc()).all()
    return jsonify({"events": [
        {**serialize_event(e), "red_flags": red_flags(e), "reports": report_count(e.id)} for e in events
    ]})


def _set_status(event_id, new_status):
    event = db.session.get(Event, event_id)
    if not event:
        return error("Event not found.", 404)
    if event.status not in ("pending", "rejected", "approved"):
        return error(f"Can't change an event that is {event.status}.", 409)
    event.status = new_status
    db.session.commit()
    return jsonify({"event": serialize_event(event)})


@bp.post("/admin/events/<int:event_id>/approve")
@roles_required("admin")
def approve(event_id):
    return _set_status(event_id, "approved")


@bp.post("/admin/events/<int:event_id>/reject")
@roles_required("admin")
def reject(event_id):
    return _set_status(event_id, "rejected")