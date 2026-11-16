"""Automatic event import from public calendar feeds (iCal / .ics links).

Colleges, clubs and communities often publish their calendars as an .ics link
(Google Calendar "public address in iCal format", Luma, Meetup...). An admin adds the link
once; the server re-reads it every hour:
- new upcoming events are added (live at once for trusted feeds, otherwise waiting for review),
- changed events are updated (time, place, title),
- events cancelled in the feed are cancelled here too.
Each imported event remembers where it came from in Event.source_url ("ics:<source id>:<event UID>").

Global events come from official event APIs the same way. A source whose url is
"ticketmaster://?city=London&countryCode=GB&classificationName=music" is read from the
Ticketmaster Discovery API (free key in TICKETMASTER_API_KEY). Those events are "external":
tickets are bought on the seller's site, not through our Razorpay checkout.
"""
import json
import threading
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity
from icalendar import Calendar

from .extensions import db
from .models import Event, EventSource, User, Venue
from .poster import find_category, find_price
from .trust import verified_domain
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



# ---------- reading an official events API (Ticketmaster Discovery) ----------

TM_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
TM_SEGMENTS = {"music": "cultural", "arts & theatre": "cultural", "sports": "sports", "film": "cultural"}


def is_ticketmaster(url):
    return url.lower().startswith("ticketmaster://")


def ticketmaster_url(city, country_code, category=""):
    params = {"city": city.strip(), "countryCode": country_code.strip().upper()}
    if category.strip():
        params["classificationName"] = category.strip()
    return "ticketmaster://?" + urllib.parse.urlencode(params)


def fetch_ticketmaster(source_url):
    key = current_app.config.get("TICKETMASTER_API_KEY")
    if not key:
        raise ValueError("Add TICKETMASTER_API_KEY to the backend .env to import global events.")
    params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(source_url).query))
    params.update({
        "apikey": key, "size": "100", "sort": "date,asc",
        "startDateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    req = urllib.request.Request(f"{TM_URL}?{urllib.parse.urlencode(params)}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read(MAX_FEED_BYTES))


def parse_ticketmaster(data, default_tz):
    """Ticketmaster JSON -> the same item dicts as parse_feed (plus city, country, price, category)."""
    items = []
    for ev in (data.get("_embedded") or {}).get("events", []):
        dates = ev.get("dates") or {}
        start_info = dates.get("start") or {}
        tz_name = dates.get("timezone") if valid_timezone(dates.get("timezone")) else default_tz
        if start_info.get("dateTime"):
            start = datetime.fromisoformat(start_info["dateTime"].replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
        elif start_info.get("localDate"):
            local = datetime.fromisoformat(f"{start_info['localDate']}T{start_info.get('localTime') or '00:00:00'}")
            start = local.replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc).replace(tzinfo=None)
        else:
            continue
        venue = ((ev.get("_embedded") or {}).get("venues") or [{}])[0]
        address = ", ".join(x for x in [venue.get("name"), (venue.get("address") or {}).get("line1")] if x)
        loc = venue.get("location") or {}
        prices = ev.get("priceRanges") or []
        segment = (((ev.get("classifications") or [{}])[0].get("segment")) or {}).get("name", "")
        items.append({
            "uid": str(ev.get("id"))[:200],
            "title": str(ev.get("name") or "")[:200],
            "description": (ev.get("info") or ev.get("pleaseNote") or None),
            "location": address or None,
            "url": ev.get("url"),
            "start": start,
            "end": None,
            "timezone": tz_name,
            "cancelled": (dates.get("status") or {}).get("code") == "cancelled",
            "city": (venue.get("city") or {}).get("name"),
            "country": (venue.get("country") or {}).get("countryCode"),
            "lat": float(loc["latitude"]) if loc.get("latitude") else None,
            "lng": float(loc["longitude"]) if loc.get("longitude") else None,
            "price": prices[0].get("min") if prices else None,
            "currency": prices[0].get("currency") if prices else None,
            "category": TM_SEGMENTS.get(segment.lower()),
        })
    return [it for it in items if it["uid"] and it["title"]]

# ---------- saving to the database ----------

def _venue_for(source, location, item=None):
    item = item or {}
    city = (item.get("city") or source.city)[:120]
    country = (item.get("country") or source.country_code)[:2].upper()
    if location:
        name, _, rest = location.partition(",")
        return Venue(name=name.strip()[:200] or city, address=rest.strip() or None, city=city, country_code=country,
                     latitude=item.get("lat"), longitude=item.get("lng"))
    return Venue(name="See event details", city=city, country_code=country)


def sync_source(source, data=None):
    """Import one feed. Returns {"created", "updated", "cancelled", "skipped"}."""
    if is_ticketmaster(source.url):
        data = data if data is not None else fetch_ticketmaster(source.url)
        items, prefix = parse_ticketmaster(data, source.timezone), "tm"
    else:
        data = data if data is not None else fetch_feed(source.url)
        items, prefix = parse_feed(data, source.timezone), "ics"
    # trusted feeds, and feeds owned by verified organizers, publish directly
    live = source.auto_approve or verified_domain(source.organizer_id) is not None
    now = utcnow_naive()
    horizon = now + timedelta(days=LOOKAHEAD_DAYS)
    counts = {"created": 0, "updated": 0, "cancelled": 0, "skipped": 0}

    for it in items:
        key = f"{prefix}:{source.id}:{it['uid']}"
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
        price = it.get("price") if it.get("price") is not None else (find_price(text) or 0)
        if event is None:
            event = Event(
                organizer_id=source.organizer_id, source_url=key, currency=(it.get("currency") or "INR")[:3],
                category=it.get("category") or find_category(text) or "other",
                price_amount=price, is_free=(price == 0),
                status="approved" if live else "pending",
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
        event.venue = _venue_for(source, it["location"], it)

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
    count = Event.query.filter(
        db.or_(Event.source_url.like(f"ics:{s.id}:%"), Event.source_url.like(f"tm:{s.id}:%")), Event.status != "cancelled",
    ).count()
    return {
        "id": s.id, "name": s.name, "url": s.url, "city": s.city, "timezone": s.timezone,
        "kind": "ticketmaster" if is_ticketmaster(s.url) else "calendar",
        "auto_approve": s.auto_approve, "organizer": {"id": s.organizer.id, "name": s.organizer.name, "email": s.organizer.email},
        "last_synced_at": to_iso_utc(s.last_synced_at), "last_result": s.last_result, "events": count,
    }


def _sync_safely(source):
    try:
        sync_source(source)
    except Exception as exc:
        db.session.rollback()
        source.last_synced_at = utcnow_naive()
        source.last_result = f"error: {exc}"[:300]
        db.session.commit()


def _new_source(d, organizer, auto_approve):
    """Validate the request body and build an EventSource (calendar link or Ticketmaster search)."""
    name = str(d.get("name") or "").strip()
    tz = str(d.get("timezone") or "Asia/Kolkata")
    if not valid_timezone(tz):
        return None, "timezone must be an IANA name, e.g. Asia/Kolkata."
    if d.get("kind") == "ticketmaster":
        city, country = str(d.get("city") or "").strip(), str(d.get("country_code") or "").strip().upper()
        if not city or len(country) != 2:
            return None, "Enter a city and a 2-letter country code, e.g. London + GB."
        url = ticketmaster_url(city, country, str(d.get("category") or ""))
        name = name or f"Ticketmaster: {city}"
    else:
        url = str(d.get("url") or "").strip()
        city, country = str(d.get("city") or "Bengaluru").strip(), str(d.get("country_code") or "IN").strip().upper()
        if not name or not url:
            return None, "Enter a name and the calendar link."
        if not url.lower().startswith(("https://", "http://", "webcal://")):
            return None, "The calendar link must start with https:// or webcal://"
    return EventSource(name=name[:200], url=url[:1000], organizer_id=organizer.id, city=city[:120],
                       country_code=country[:2] or "IN", timezone=tz, auto_approve=auto_approve), None


# admin: any feed, for any organizer account

@bp.get("/admin/sources")
@roles_required("admin")
def list_sources():
    return jsonify({"sources": [serialize_source(s) for s in EventSource.query.order_by(EventSource.id).all()]})


@bp.post("/admin/sources")
@roles_required("admin")
def add_source():
    """Body: {name, url, organizer_email, city?, timezone?, auto_approve?} or
    {kind: "ticketmaster", city, country_code, category?, organizer_email}. Imports once straight away."""
    d = request.get_json(silent=True) or {}
    organizer = User.query.filter_by(email=str(d.get("organizer_email") or "").strip().lower()).first()
    if not organizer or organizer.role not in ("organizer", "admin"):
        return error("organizer_email must be an existing organizer account.")
    source, problem = _new_source(d, organizer, bool(d.get("auto_approve")))
    if problem:
        return error(problem)
    db.session.add(source)
    db.session.commit()
    _sync_safely(source)
    return jsonify({"source": serialize_source(source)}), 201


@bp.post("/admin/sources/<int:source_id>/sync")
@roles_required("admin")
def sync_one(source_id):
    source = db.session.get(EventSource, source_id)
    if not source:
        return error("Feed not found.", 404)
    _sync_safely(source)
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


# organizer: their own calendar feeds (self-serve)

MAX_FEEDS_PER_ORGANIZER = 5


def _own_source(source_id):
    source = db.session.get(EventSource, source_id)
    if not source or source.organizer_id != int(get_jwt_identity()):
        return None
    return source


@bp.get("/organizer/sources")
@roles_required("organizer", "admin")
def my_sources():
    mine = EventSource.query.filter_by(organizer_id=int(get_jwt_identity())).order_by(EventSource.id).all()
    return jsonify({"sources": [serialize_source(s) for s in mine]})


@bp.post("/organizer/sources")
@roles_required("organizer", "admin")
def add_my_source():
    """Body: {name, url, city?}. Organizers connect their club calendar; events of verified organizers go live directly."""
    d = request.get_json(silent=True) or {}
    user = db.session.get(User, int(get_jwt_identity()))
    if EventSource.query.filter_by(organizer_id=user.id).count() >= MAX_FEEDS_PER_ORGANIZER:
        return error(f"You can connect up to {MAX_FEEDS_PER_ORGANIZER} calendars.")
    d = {**d, "kind": "calendar"}   # organizers connect calendars; global API sources are admin-only
    source, problem = _new_source(d, user, auto_approve=False)
    if problem:
        return error(problem)
    db.session.add(source)
    db.session.commit()
    _sync_safely(source)
    return jsonify({"source": serialize_source(source)}), 201


@bp.post("/organizer/sources/<int:source_id>/sync")
@roles_required("organizer", "admin")
def sync_my_source(source_id):
    source = _own_source(source_id)
    if not source:
        return error("Feed not found.", 404)
    _sync_safely(source)
    return jsonify({"source": serialize_source(source)})


@bp.delete("/organizer/sources/<int:source_id>")
@roles_required("organizer", "admin")
def delete_my_source(source_id):
    source = _own_source(source_id)
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