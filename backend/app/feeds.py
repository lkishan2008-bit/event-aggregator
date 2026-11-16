"""Automatic event import from public calendar feeds (iCal / .ics links).

Colleges, clubs and communities often publish their calendars as an .ics link
(Google Calendar "public address in iCal format", Luma, Meetup...). An admin adds the link
once; the server re-reads it every hour:
- new upcoming events are added (live at once for trusted feeds, otherwise waiting for review),
- changed events are updated (time, place, title),
- events cancelled in the feed are cancelled here too.
Each imported event remembers where it came from in Event.source_url ("ics:<source id>:<event UID>").
"""
import threading
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request
from icalendar import Calendar

from .extensions import db
from .models import Event, EventSource, User, Venue
from .poster import find_category, find_price
from .utils import error, roles_required, to_iso_utc, utcnow_naive, valid_timezone

bp = Blueprint("feeds", __name__, url_prefix="/api")

MAX_FEED_BYTES = 3 * 1024 * 1024
LOOKAHEAD_DAYS = 180


# ---------- reading a feed ----------

def fetch_feed(url):
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Feed link must start with https:// or webcal://")
    req = urllib.request.Request(url, headers={"User-Agent": "EventAggregator/1.0 (+calendar import)"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = res.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("Feed is too large.")
    return data


def _to_utc(value, default_tz):
    """iCal start/end -> (UTC naive datetime, IANA timezone name)."""
    if isinstance(value, datetime):
        if value.tzinfo is None:  # "floating" time: use the feed's timezone
            value = value.replace(tzinfo=ZoneInfo(default_tz))
        tz_name = getattr(value.tzinfo, "key", None) or default_tz
        return value.astimezone(timezone.utc).replace(tzinfo=None), tz_name
    if isinstance(value, date):  # all-day event
        local = datetime(value.year, value.month, value.day, tzinfo=ZoneInfo(default_tz))
        return local.astimezone(timezone.utc).replace(tzinfo=None), default_tz
    return None, default_tz


def parse_feed(data, default_tz):
    """Returns a list of plain dicts, one per event in the feed."""
    cal = Calendar.from_ical(data)
    items = []
    for comp in cal.walk("VEVENT"):
        uid = str(comp.get("UID") or "").strip()
        title = str(comp.get("SUMMARY") or "").strip()
        if not uid or not title or not comp.get("DTSTART"):
            continue
        start, tz_name = _to_utc(comp.decoded("DTSTART"), default_tz)
        end = _to_utc(comp.decoded("DTEND"), default_tz)[0] if comp.get("DTEND") else None
        if start is None:
            continue
        items.append({
            "uid": uid[:200],
            "title": title[:200],
            "description": str(comp.get("DESCRIPTION") or "").strip()[:4000] or None,
            "location": str(comp.get("LOCATION") or "").strip()[:500] or None,
            "url": str(comp.get("URL") or "").strip()[:500] or None,
            "start": start,
            "end": end if end and end >= start else None,
            "timezone": tz_name if valid_timezone(tz_name) else default_tz,
            "cancelled": str(comp.get("STATUS") or "").upper() == "CANCELLED",
        })
    return items


# ---------- saving to the database ----------

def _venue_for(source, location):
    if location:
        name, _, rest = location.partition(",")
        return Venue(name=name.strip()[:200] or source.city, address=rest.strip() or None,
                     city=source.city, country_code=source.country_code)
    return Venue(name="See event details", city=source.city, country_code=source.country_code)


def sync_source(source, data=None):
    """Import one feed. Returns {"created", "updated", "cancelled", "skipped"}."""
    data = data if data is not None else fetch_feed(source.url)
    items = parse_feed(data, source.timezone)
    now = utcnow_naive()
    horizon = now + timedelta(days=LOOKAHEAD_DAYS)
    counts = {"created": 0, "updated": 0, "cancelled": 0, "skipped": 0}

    for it in items:
        key = f"ics:{source.id}:{it['uid']}"
        event = Event.query.filter_by(source_url=key).first()
        ends = it["end"] or it["start"]

        if it["cancelled"]:
            if event and event.status != "cancelled":
                event.status = "cancelled"
                counts["cancelled"] += 1
            continue
        if ends < now or it["start"] > horizon:
            counts["skipped"] += 1  # past, or too far ahead
            continue

        text = f"{it['title']}\n{it['description'] or ''}"
        price = find_price(text) or 0
        if event is None:
            event = Event(
                organizer_id=source.organizer_id, source_url=key, currency="INR",
                category=find_category(text) or "other",
                price_amount=price, is_free=(price == 0),
                status="approved" if source.auto_approve else "pending",
            )
            db.session.add(event)
            counts["created"] += 1
        else:
            changed = (event.title, event.start_utc, event.end_utc, event.description) != (it["title"], it["start"], it["end"], it["description"])
            if not changed and (event.venue.name if event.venue else None) == (it["location"] or "See event details").partition(",")[0].strip():
                continue
            counts["updated"] += 1

        event.title = it["title"]
        event.description = it["description"]
        event.start_utc = it["start"]
        event.end_utc = it["end"]
        event.timezone = it["timezone"]
        event.registration_url = it["url"] or event.registration_url
        event.venue = _venue_for(source, it["location"])

    source.last_synced_at = now
    source.last_result = ", ".join(f"{v} {k}" for k, v in counts.items())
    db.session.commit()
    return counts


def sync_all():
    results = {}
    for source in EventSource.query.all():
        try:
            results[source.id] = sync_source(source)
        except Exception as exc:  # one broken feed must not stop the others
            db.session.rollback()
            source.last_synced_at = utcnow_naive()
            source.last_result = f"error: {exc}"[:300]
            db.session.commit()
            results[source.id] = {"error": str(exc)}
    return results


def start_background_sync(app):
    """Re-import all feeds every FEED_SYNC_MINUTES while the server runs."""
    minutes = app.config.get("FEED_SYNC_MINUTES", 0)
    if not minutes:
        return

    def loop():
        time.sleep(10)  # let the server start first
        while True:
            with app.app_context():
                try:
                    sync_all()
                except Exception as exc:
                    app.logger.warning("feed sync failed: %s", exc)
            time.sleep(minutes * 60)

    threading.Thread(target=loop, daemon=True, name="feed-sync").start()


# ---------- API ----------

def serialize_source(s):
    count = Event.query.filter(Event.source_url.like(f"ics:{s.id}:%"), Event.status != "cancelled").count()
    return {
        "id": s.id, "name": s.name, "url": s.url, "city": s.city, "timezone": s.timezone,
        "auto_approve": s.auto_approve, "organizer": {"id": s.organizer.id, "name": s.organizer.name, "email": s.organizer.email},
        "last_synced_at": to_iso_utc(s.last_synced_at), "last_result": s.last_result, "events": count,
    }


@bp.get("/admin/sources")
@roles_required("admin")
def list_sources():
    return jsonify({"sources": [serialize_source(s) for s in EventSource.query.order_by(EventSource.id).all()]})


@bp.post("/admin/sources")
@roles_required("admin")
def add_source():
    """Body: {name, url, organizer_email, city?, timezone?, auto_approve?}. Imports the feed once straight away."""
    d = request.get_json(silent=True) or {}
    name, url = str(d.get("name") or "").strip(), str(d.get("url") or "").strip()
    organizer = User.query.filter_by(email=str(d.get("organizer_email") or "").strip().lower()).first()
    tz = str(d.get("timezone") or "Asia/Kolkata")
    if not name or not url:
        return error("Enter a name and the calendar link.")
    if not url.lower().startswith(("https://", "http://", "webcal://")):
        return error("The calendar link must start with https:// or webcal://")
    if not organizer or organizer.role not in ("organizer", "admin"):
        return error("organizer_email must be an existing organizer account.")
    if not valid_timezone(tz):
        return error("timezone must be an IANA name, e.g. Asia/Kolkata.")

    source = EventSource(name=name[:200], url=url[:1000], organizer_id=organizer.id,
                         city=str(d.get("city") or "Bengaluru").strip()[:120], timezone=tz,
                         auto_approve=bool(d.get("auto_approve")))
    db.session.add(source)
    db.session.commit()
    try:
        sync_source(source)
    except Exception as exc:
        db.session.rollback()
        source.last_synced_at = utcnow_naive()
        source.last_result = f"error: {exc}"[:300]
        db.session.commit()
    return jsonify({"source": serialize_source(source)}), 201


@bp.post("/admin/sources/<int:source_id>/sync")
@roles_required("admin")
def sync_one(source_id):
    source = db.session.get(EventSource, source_id)
    if not source:
        return error("Feed not found.", 404)
    try:
        sync_source(source)
    except Exception as exc:
        db.session.rollback()
        source.last_synced_at = utcnow_naive()
        source.last_result = f"error: {exc}"[:300]
        db.session.commit()
    return jsonify({"source": serialize_source(source)})


@bp.delete("/admin/sources/<int:source_id>")
@roles_required("admin")
def delete_source(source_id):
    """Stops importing. Events already imported stay (organizers may have registrations on them)."""
    source = db.session.get(EventSource, source_id)
    if not source:
        return error("Feed not found.", 404)
    db.session.delete(source)
    db.session.commit()
    return jsonify({"deleted": source_id})


@bp.post("/cron/sync-feeds")
def cron_sync():
    """For an external scheduler (e.g. cron-job.org) on hosting that sleeps: header X-Cron-Secret required."""
    secret = current_app.config.get("CRON_SECRET")
    if not secret or request.headers.get("X-Cron-Secret") != secret:
        return error("Not allowed.", 403)
    return jsonify({"results": sync_all()})