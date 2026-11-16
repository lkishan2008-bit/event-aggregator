from datetime import datetime, timedelta, timezone


def make_event(client, headers, **over):
    start = datetime.now(timezone.utc) + timedelta(days=3)
    body = {
        "title": "HackRV", "category": "hackathon", "start_utc": start.isoformat(),
        "end_utc": (start + timedelta(hours=6)).isoformat(), "timezone": "Asia/Kolkata",
        "price_amount": 0, "currency": "INR", "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "IN"},
    }
    body.update(over)
    return client.post("/api/events", json=body, headers=headers).get_json()["event"]["id"]


def test_checkin_flow_and_live_stats(app, client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    org = auth.signup("o@x.co", "organizer")
    other_org = auth.signup("o2@x.co", "organizer")
    student = auth.signup("s@x.co")

    eid = make_event(client, org)
    client.post(f"/api/admin/events/{eid}/approve", headers=admin)
    other_eid = make_event(client, admin, title="Other")

    reg = client.post(f"/api/events/{eid}/register", headers=student).get_json()["registration"]
    code = reg["qr_token"]

    # confirmation email went out
    mails = [m for m in app.extensions["outbox"] if m["to"] == "s@x.co"]
    assert mails[-1]["subject"] == "You're going: HackRV"

    url = f"/api/organizer/events/{eid}/checkin"
    assert client.post(url, json={"code": code}, headers=student).status_code == 403      # students can't scan
    assert client.post(url, json={"code": code}, headers=other_org).status_code == 404    # not their event
    assert client.post(url, json={"code": "nope"}, headers=org).get_json()["result"] == "invalid"
    assert client.post(f"/api/organizer/events/{other_eid}/checkin", json={"code": code}, headers=admin).get_json()["result"] == "wrong_event"

    ok = client.post(url, json={"code": code}, headers=org)
    assert ok.status_code == 200 and ok.get_json()["attendee"]["name"] == "U"
    again = client.post(url, json={"code": code}, headers=org)
    assert again.status_code == 200 and again.get_json()["result"] == "already"

    s = client.get(f"/api/organizer/events/{eid}/checkins", headers=org).get_json()
    assert s["going"] == 1 and s["checked_in"] == 1 and s["recent"][0]["email"] == "s@x.co"

    # the student's pass now shows checked in, and can't be cancelled
    mine = client.get(f"/api/events/{eid}/my-registration", headers=student).get_json()["registration"]
    assert mine["checked_in_at"] is not None
    assert client.delete(f"/api/events/{eid}/register", headers=student).status_code == 409