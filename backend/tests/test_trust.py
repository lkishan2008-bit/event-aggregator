import re
from datetime import datetime, timedelta, timezone


def make_event(client, headers, **over):
    start = datetime.now(timezone.utc) + timedelta(days=3)
    body = {
        "title": "Design Sprint", "category": "workshop", "start_utc": start.isoformat(),
        "end_utc": (start + timedelta(hours=3)).isoformat(), "timezone": "Asia/Kolkata",
        "price_amount": 0, "currency": "INR", "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "IN"},
    }
    body.update(over)
    r = client.post("/api/events", json=body, headers=headers)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["event"]


def code_sent_to(app, email):
    mails = [m for m in app.extensions["outbox"] if m["to"] == email]
    return re.search(r"\b(\d{6})\b", mails[-1]["subject"]).group(1)


def test_verified_organizer_clean_event_goes_live(app, client, auth):
    org = auth.signup("club@gmail.com", "organizer")

    # unverified: waits for review, and the admin sees why
    assert make_event(client, org)["status"] == "pending"

    # only official college emails can be used
    assert client.post("/api/organizer/verify/start", json={"email": "me@gmail.com"}, headers=org).status_code == 400
    assert client.post("/api/organizer/verify/start", json={"email": "codingclub@rvce.edu.in"}, headers=org).status_code == 200
    bad = client.post("/api/organizer/verify/confirm", json={"code": "000000"}, headers=org)
    assert bad.status_code == 400
    ok = client.post("/api/organizer/verify/confirm", json={"code": code_sent_to(app, "codingclub@rvce.edu.in")}, headers=org)
    assert ok.status_code == 200
    assert client.get("/api/organizer/verification", headers=org).get_json()["verification"]["verified"] is True

    ev = make_event(client, org, title="Git Workshop")
    assert ev["status"] == "approved" and ev["organizer"]["verified_domain"] == "rvce.edu.in"

    # verified but suspicious -> still goes to review
    sus = make_event(client, org, title="Cheap Fest", description="Pay Rs 99 on gpay 9876543210 to confirm your seat")
    assert sus["status"] == "pending"


def test_red_flags_shown_to_admin(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    org = auth.signup("o@x.co", "organizer")
    make_event(client, org, title="Mega Hack", description="Send entry fee to megahack@okaxis. 100% placement guaranteed!", price_amount=9999)
    events = client.get("/api/admin/events?status=pending", headers=admin).get_json()["events"]
    flags = events[0]["red_flags"]
    assert "Asks to pay outside the app (UPI ID or payment number)" in flags
    assert "Spam-like promises in the text" in flags
    assert "Unusually high price" in flags
    assert "Organizer is not verified" in flags
    assert events[0]["reports"] == 0


def test_reports_hide_event_after_three(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    ev = make_event(client, admin, title="Suspicious Night")
    assert ev["status"] == "approved"
    students = [auth.signup(f"s{i}@x.co") for i in range(3)]

    assert client.post(f"/api/events/{ev['id']}/report", json={"reason": "nope"}, headers=students[0]).status_code == 400
    for i, s in enumerate(students):
        r = client.post(f"/api/events/{ev['id']}/report", json={"reason": "fake", "details": "no such event"}, headers=s).get_json()
        assert r["hidden"] is (i == 2)
    # same user reporting twice doesn't count twice
    assert client.post(f"/api/events/{ev['id']}/report", json={"reason": "fake"}, headers=students[0]).status_code == 404  # hidden now

    titles = [e["title"] for e in client.get("/api/events").get_json()["events"]]
    assert "Suspicious Night" not in titles
    pending = client.get("/api/admin/events?status=pending", headers=admin).get_json()["events"]
    assert pending[0]["reports"] == 3
    assert len(client.get(f"/api/admin/events/{ev['id']}/reports", headers=admin).get_json()["reports"]) == 3