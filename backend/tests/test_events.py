from datetime import datetime, timedelta, timezone

from app.extensions import db


def iso(days, hours=0):
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()


def event_body(**over):
    body = {
        "title": "HackRV", "category": "hackathon", "start_utc": iso(3), "end_utc": iso(3, 6),
        "timezone": "Asia/Kolkata", "price_amount": 0, "currency": "inr",
        "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "in"},
    }
    body.update(over)
    return body


def test_full_flow_submit_approve_list(client, auth):
    org = auth.signup("org@x.co", "organizer")
    admin = auth.login("admin@x.co", "Admin@12345")

    r = client.post("/api/events", json=event_body(), headers=org)
    assert r.status_code == 201
    ev = r.get_json()["event"]
    assert ev["status"] == "pending" and ev["currency"] == "INR" and ev["is_free"]

    # pending events are hidden from the public feed and detail page
    assert client.get("/api/events").get_json()["total"] == 0
    assert client.get(f"/api/events/{ev['id']}").status_code == 404
    # but the owner can see it
    assert client.get(f"/api/events/{ev['id']}", headers=org).status_code == 200

    pending = client.get("/api/admin/events?status=pending", headers=admin).get_json()["events"]
    assert [e["id"] for e in pending] == [ev["id"]]

    assert client.post(f"/api/admin/events/{ev['id']}/approve", headers=admin).status_code == 200
    feed = client.get("/api/events").get_json()
    assert feed["total"] == 1 and feed["events"][0]["venue"]["city"] == "Bengaluru"


def test_admin_events_auto_approved_and_filters(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    client.post("/api/events", json=event_body(title="Free Hack"), headers=admin)
    client.post("/api/events", json=event_body(title="Paid Fest", category="fest", price_amount=199), headers=admin)
    client.post("/api/events", json=event_body(title="Tokyo Meetup", category="meetup", timezone="Asia/Tokyo",
                                                venue={"name": "Shibuya", "city": "Tokyo", "country_code": "JP"}),
                headers=admin)

    assert client.get("/api/events").get_json()["total"] == 3
    assert client.get("/api/events?free=1").get_json()["total"] == 2
    assert client.get("/api/events?category=fest").get_json()["events"][0]["title"] == "Paid Fest"
    assert client.get("/api/events?city=tokyo").get_json()["events"][0]["timezone"] == "Asia/Tokyo"
    assert client.get("/api/events?country=JP").get_json()["total"] == 1
    assert client.get("/api/events?q=hack").get_json()["total"] == 1


def test_permissions_and_validation(client, auth):
    student = auth.signup("s@x.co", "student")
    org = auth.signup("o@x.co", "organizer")

    assert client.post("/api/events", json=event_body()).status_code == 401
    assert client.post("/api/events", json=event_body(), headers=student).status_code == 403
    assert client.get("/api/admin/events", headers=org).status_code == 403

    bad = [
        event_body(title=""),
        event_body(category="party"),
        event_body(start_utc="2026-11-22T09:00:00"),          # no timezone
        event_body(start_utc=iso(-1), end_utc=iso(-1, 2)),     # in the past
        event_body(end_utc=iso(2)),                            # ends before start
        event_body(timezone="Mars/Base"),
        event_body(price_amount=-5),
        event_body(currency="RUPEES"),
        event_body(venue={"name": "X"}),
    ]
    for body in bad:
        assert client.post("/api/events", json=body, headers=org).status_code == 400, body


def test_past_events_hidden(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    client.post("/api/events", json=event_body(), headers=admin)
    with client.application.app_context():
        from app.models import Event
        e = Event.query.first()
        e.start_utc = e.start_utc - timedelta(days=10)
        e.end_utc = e.end_utc - timedelta(days=10)
        db.session.commit()
    assert client.get("/api/events").get_json()["total"] == 0