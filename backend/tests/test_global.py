from datetime import datetime, timedelta, timezone

import app.feeds as feeds


def tm_payload(start):
    return {"_embedded": {"events": [
        {
            "id": "G5vYZ9", "name": "Coldplay: Music of the Spheres", "url": "https://www.ticketmaster.co.uk/coldplay",
            "dates": {"start": {"dateTime": start.strftime("%Y-%m-%dT%H:%M:%SZ")}, "timezone": "Europe/London", "status": {"code": "onsale"}},
            "priceRanges": [{"min": 85.0, "currency": "GBP"}],
            "classifications": [{"segment": {"name": "Music"}}],
            "_embedded": {"venues": [{"name": "Wembley Stadium", "city": {"name": "London"}, "country": {"countryCode": "GB"},
                                      "address": {"line1": "Wembley"}, "location": {"latitude": "51.556", "longitude": "-0.279"}}]},
        },
        {
            "id": "OLD1", "name": "Cancelled Show",
            "dates": {"start": {"localDate": (start + timedelta(days=1)).strftime("%Y-%m-%d"), "localTime": "19:30:00"},
                      "timezone": "Europe/London", "status": {"code": "cancelled"}},
        },
    ]}}


def test_ticketmaster_import_is_global_and_external(app, client, auth, monkeypatch):
    admin = auth.login("admin@x.co", "Admin@12345")
    student = auth.signup("s@x.co")
    start = datetime.now(timezone.utc) + timedelta(days=20)

    # without a key: clear error, nothing imported
    r = client.post("/api/admin/sources", headers=admin, json={"kind": "ticketmaster", "city": "London", "country_code": "gb", "organizer_email": "admin@x.co"})
    assert r.status_code == 201 and "TICKETMASTER_API_KEY" in r.get_json()["source"]["last_result"]

    app.config["TICKETMASTER_API_KEY"] = "test-key"
    monkeypatch.setattr(feeds, "fetch_ticketmaster", lambda url: tm_payload(start))
    r = client.post("/api/admin/sources", headers=admin, json={
        "kind": "ticketmaster", "city": "London", "country_code": "GB", "category": "music",
        "organizer_email": "admin@x.co", "auto_approve": True,
    })
    src = r.get_json()["source"]
    assert src["kind"] == "ticketmaster" and src["events"] == 1 and "classificationName=music" in src["url"]

    ev = next(e for e in client.get("/api/events").get_json()["events"] if e["title"].startswith("Coldplay"))
    assert ev["venue"]["city"] == "London" and ev["venue"]["country_code"] == "GB" and ev["venue"]["latitude"] == 51.556
    assert ev["currency"] == "GBP" and ev["price_amount"] == 85 and ev["category"] == "cultural"
    assert ev["timezone"] == "Europe/London" and ev["external"] is True
    assert ev["registration_url"] == "https://www.ticketmaster.co.uk/coldplay"

    # tickets are bought on the seller's site, never through our checkout
    assert client.post(f"/api/events/{ev['id']}/register", headers=student).status_code == 400


def test_organizer_connects_own_calendar(client, auth, monkeypatch):
    org = auth.signup("club@x.co", "organizer")
    other = auth.signup("other@x.co", "organizer")
    start = datetime.now(timezone.utc) + timedelta(days=4)
    fmt = "%Y%m%dT%H%M%SZ"
    ics = ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:x\r\nBEGIN:VEVENT\r\nUID:c1\r\nSUMMARY:Club Robotics Night\r\n"
           f"DTSTART:{start.strftime(fmt)}\r\nLOCATION:BMSCE Lab 2\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n").encode()
    monkeypatch.setattr(feeds, "fetch_feed", lambda url: ics)

    r = client.post("/api/organizer/sources", headers=org, json={"name": "Robotics Club", "url": "https://calendar.example.com/r.ics"})
    assert r.status_code == 201
    src = r.get_json()["source"]
    assert src["events"] == 1 and src["kind"] == "calendar"
    assert [s["name"] for s in client.get("/api/organizer/sources", headers=org).get_json()["sources"]] == ["Robotics Club"]

    # unverified organizer: imported events wait for admin review
    mine = client.get("/api/organizer/events", headers=org).get_json()["events"]
    assert mine[0]["title"] == "Club Robotics Night" and mine[0]["status"] == "pending"

    # another organizer can't touch it, and students can't add feeds
    assert client.post(f"/api/organizer/sources/{src['id']}/sync", headers=other).status_code == 404
    assert client.delete(f"/api/organizer/sources/{src['id']}", headers=other).status_code == 404
    assert client.delete(f"/api/organizer/sources/{src['id']}", headers=org).status_code == 200