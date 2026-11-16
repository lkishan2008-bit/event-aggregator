from datetime import datetime, timedelta, timezone


def iso(days, hours=0):
    return (datetime.now(timezone.utc) + timedelta(days=days, hours=hours)).isoformat()


def make_event(client, admin, **over):
    body = {
        "title": "HackRV", "category": "hackathon", "start_utc": iso(3), "end_utc": iso(3, 6),
        "timezone": "Asia/Kolkata", "price_amount": 0, "currency": "INR",
        "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "IN"},
    }
    body.update(over)
    return client.post("/api/events", json=body, headers=admin).get_json()["event"]["id"]


def test_register_pass_cancel_and_count(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    student = auth.signup("s@x.co")
    eid = make_event(client, admin)

    assert client.get(f"/api/events/{eid}/my-registration", headers=student).get_json()["registration"] is None

    r = client.post(f"/api/events/{eid}/register", headers=student)
    assert r.status_code == 201
    reg = r.get_json()["registration"]
    assert reg["status"] == "registered" and len(reg["qr_token"]) > 20 and reg["event"]["going"] == 1

    # registering twice returns the same pass, count stays 1
    again = client.post(f"/api/events/{eid}/register", headers=student).get_json()["registration"]
    assert again["qr_token"] == reg["qr_token"] and again["event"]["going"] == 1
    assert client.get(f"/api/events/{eid}").get_json()["event"]["going"] == 1

    passes = client.get("/api/me/registrations", headers=student).get_json()["registrations"]
    assert [p["event"]["id"] for p in passes] == [eid]

    assert client.delete(f"/api/events/{eid}/register", headers=student).status_code == 200
    assert client.get(f"/api/events/{eid}").get_json()["event"]["going"] == 0
    assert client.get("/api/me/registrations", headers=student).get_json()["registrations"] == []
    assert client.delete(f"/api/events/{eid}/register", headers=student).status_code == 404

    # can register again after cancelling, same pass token
    r = client.post(f"/api/events/{eid}/register", headers=student)
    assert r.status_code == 201 and r.get_json()["registration"]["qr_token"] == reg["qr_token"]


def test_cannot_register_for_pending_or_missing_events(client, auth):
    org = auth.signup("o@x.co", "organizer")
    student = auth.signup("s@x.co")
    pending = make_event(client, org)  # organizer events start pending
    assert client.post(f"/api/events/{pending}/register", headers=student).status_code == 400
    assert client.post("/api/events/999/register", headers=student).status_code == 404
    assert client.post(f"/api/events/{pending}/register").status_code == 401