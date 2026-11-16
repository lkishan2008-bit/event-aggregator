import re


def code_for(app, email):
    mails = [m for m in app.extensions["outbox"] if m["to"] == email]
    return re.search(r"\b(\d{6})\b", mails[-1]["subject"]).group(1)


def test_save_and_list(client, auth):
    student = auth.signup("s@x.co")
    events = client.get("/api/events").get_json()["events"]
    assert events == []  # empty test db: create one as admin
    admin = auth.login("admin@x.co", "Admin@12345")
    from datetime import datetime, timedelta, timezone
    start = datetime.now(timezone.utc) + timedelta(days=2)
    eid = client.post("/api/events", headers=admin, json={
        "title": "Saved Fest", "category": "fest", "start_utc": start.isoformat(), "timezone": "Asia/Kolkata",
        "price_amount": 0, "currency": "INR", "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "IN"},
    }).get_json()["event"]["id"]

    assert client.post(f"/api/events/{eid}/save", headers=student).get_json()["saved"] is True
    assert client.post(f"/api/events/{eid}/save", headers=student).status_code == 200      # saving twice is fine
    saved = client.get("/api/me/saved", headers=student).get_json()
    assert [e["title"] for e in saved["events"]] == ["Saved Fest"] and saved["ids"] == [eid]
    client.delete(f"/api/events/{eid}/save", headers=student)
    assert client.get("/api/me/saved", headers=student).get_json()["events"] == []
    assert client.post("/api/events/999/save", headers=student).status_code == 404


def test_forgot_and_reset_password(app, client, auth):
    auth.signup("s@x.co")
    # unknown email gets the same answer (no account fishing)
    assert client.post("/api/auth/forgot", json={"email": "nobody@x.co"}).get_json()["sent"] is True
    assert client.post("/api/auth/forgot", json={"email": "s@x.co"}).status_code == 200
    code = code_for(app, "s@x.co")

    weak = client.post("/api/auth/reset", json={"email": "s@x.co", "code": code, "password": "weak"})
    assert weak.status_code == 400 and "uppercase" in weak.get_json()["error"]
    assert client.post("/api/auth/reset", json={"email": "s@x.co", "code": "000000", "password": "NewPass@123"}).status_code == 400
    ok = client.post("/api/auth/reset", json={"email": "s@x.co", "code": code, "password": "NewPass@123"})
    assert ok.status_code == 200

    # old password no longer works, new one does (login then asks for the usual OTP)
    assert client.post("/api/auth/login", json={"email": "s@x.co", "password": "Secret@123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "s@x.co", "password": "NewPass@123"}).status_code == 200