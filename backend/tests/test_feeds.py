from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.feeds import sync_source
from app.models import Event, EventSource


def ics(events):
    body = "".join(events)
    return f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n{body}END:VCALENDAR\r\n".encode()


def vevent(uid, title, start, hours=3, location="IISc Main Auditorium, CV Raman Road", status="CONFIRMED", extra=""):
    fmt = "%Y%m%dT%H%M%SZ"
    end = start + timedelta(hours=hours)
    return (f"BEGIN:VEVENT\r\nUID:{uid}\r\nSUMMARY:{title}\r\nDTSTART:{start.strftime(fmt)}\r\nDTEND:{end.strftime(fmt)}\r\n"
            f"LOCATION:{location}\r\nSTATUS:{status}\r\n{extra}END:VEVENT\r\n")


def test_import_update_and_cancel(app, client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    auth.signup("club@x.co", "organizer")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    soon, later = now + timedelta(days=3), now + timedelta(days=10)

    feed1 = ics([
        vevent("a1", "AI Hackathon", soon, extra="DESCRIPTION:Entry fee Rs 100\r\nURL:https://example.com/ai\r\n"),
        vevent("b2", "Python Workshop", later),
        vevent("old", "Last Month Talk", now - timedelta(days=30)),
        "BEGIN:VEVENT\r\nUID:allday\r\nSUMMARY:Open Day\r\nDTSTART;VALUE=DATE:" + later.strftime("%Y%m%d") + "\r\nEND:VEVENT\r\n",
    ])

    # adding a source imports it straight away (the network fetch is replaced by our test feed)
    import app.feeds as feeds
    feeds_fetch = feeds.fetch_feed
    feeds.fetch_feed = lambda url: feed1
    try:
        r = client.post("/api/admin/sources", headers=admin, json={
            "name": "IISc Clubs", "url": "webcal://calendar.example.com/iisc.ics", "organizer_email": "club@x.co", "auto_approve": True,
        })
    finally:
        feeds.fetch_feed = feeds_fetch
    assert r.status_code == 201, r.get_json()
    src = r.get_json()["source"]
    assert src["events"] == 3 and src["last_result"].startswith("3 created")

    titles = {e["title"]: e for e in client.get("/api/events").get_json()["events"]}
    assert {"AI Hackathon", "Python Workshop", "Open Day"} <= set(titles)       # live in the public feed
    assert "Last Month Talk" not in titles                                      # past events skipped
    ai = titles["AI Hackathon"]
    assert ai["category"] == "hackathon" and ai["price_amount"] == 100 and ai["registration_url"] == "https://example.com/ai"
    assert ai["venue"]["name"] == "IISc Main Auditorium" and ai["venue"]["city"] == "Bengaluru"

    # next hourly sync: one event moved, one cancelled -> updated in place, no duplicates
    source = db.session.get(EventSource, src["id"])
    feed2 = ics([vevent("a1", "AI Hackathon", soon + timedelta(hours=2)), vevent("b2", "Python Workshop", later, status="CANCELLED")])
    counts = sync_source(source, data=feed2)
    assert counts["updated"] == 1 and counts["cancelled"] == 1 and counts["created"] == 0
    assert Event.query.filter(Event.source_url.like("ics:%:a1")).count() == 1
    titles = {e["title"] for e in client.get("/api/events").get_json()["events"]}
    assert "Python Workshop" not in titles


def test_untrusted_feed_waits_for_review_and_permissions(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    org = auth.signup("club@x.co", "organizer")
    import app.feeds as feeds
    start = datetime.now(timezone.utc) + timedelta(days=2)
    original = feeds.fetch_feed
    feeds.fetch_feed = lambda url: ics([vevent("x", "Robotics Meetup", start)])
    try:
        assert client.post("/api/admin/sources", headers=org, json={"name": "x", "url": "https://x", "organizer_email": "club@x.co"}).status_code == 403
        r = client.post("/api/admin/sources", headers=admin, json={"name": "Robo Club", "url": "https://x/robo.ics", "organizer_email": "club@x.co"})
    finally:
        feeds.fetch_feed = original
    assert r.status_code == 201
    pending = [e["title"] for e in client.get("/api/admin/events?status=pending", headers=admin).get_json()["events"]]
    assert "Robotics Meetup" in pending                                          # not trusted: admin reviews first
    assert client.post("/api/cron/sync-feeds").status_code == 403                # cron URL needs the secret