import hashlib
import hmac
from datetime import datetime, timedelta, timezone


def make_paid_event(client, admin, price=199):
    start = datetime.now(timezone.utc) + timedelta(days=3)
    body = {
        "title": "Paid Hack", "category": "hackathon", "start_utc": start.isoformat(),
        "end_utc": (start + timedelta(hours=6)).isoformat(), "timezone": "Asia/Kolkata",
        "price_amount": price, "currency": "INR", "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "IN"},
    }
    return client.post("/api/events", json=body, headers=admin).get_json()["event"]["id"]


def test_paid_ticket_needs_verified_payment_mock_mode(app, client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    student = auth.signup("s@x.co")
    eid = make_paid_event(client, admin)

    r = client.post(f"/api/events/{eid}/register", headers=student)
    assert r.status_code == 200
    body = r.get_json()
    pay = body["payment"]
    assert body["registration"]["status"] == "pending_payment" and body["registration"]["qr_token"] is None
    assert pay["mock"] is True and pay["amount"] == 19900 and pay["currency"] == "INR"
    assert client.get(f"/api/events/{eid}").get_json()["event"]["going"] == 0      # not going until paid
    assert client.get("/api/me/registrations", headers=student).get_json()["registrations"] == []

    url = f"/api/events/{eid}/pay/verify"
    bad = client.post(url, json={"order_id": pay["id"], "payment_id": "x", "signature": "fake"}, headers=student)
    assert bad.status_code == 400

    ok = client.post(url, json={"order_id": pay["id"], "payment_id": "pay_mock", "signature": "mock-paid"}, headers=student)
    reg = ok.get_json()["registration"]
    assert ok.status_code == 200 and reg["status"] == "registered" and reg["qr_token"] and reg["amount_paid"] == 199
    assert client.get(f"/api/events/{eid}").get_json()["event"]["going"] == 1
    assert any(m["subject"] == "You're going: Paid Hack" for m in app.extensions["outbox"])

    # paid tickets can't be self-cancelled
    assert client.delete(f"/api/events/{eid}/register", headers=student).status_code == 409


def test_real_razorpay_signature_check(app, client, auth, monkeypatch):
    app.config.update(RAZORPAY_KEY_ID="rzp_test_x", RAZORPAY_KEY_SECRET="secret123")
    monkeypatch.setattr("app.registrations.create_order", lambda amount, currency, receipt: {
        "id": "order_ABC", "amount": amount, "currency": currency, "key_id": "rzp_test_x", "mock": False})
    admin = auth.login("admin@x.co", "Admin@12345")
    student = auth.signup("s@x.co")
    eid = make_paid_event(client, admin)
    assert client.post(f"/api/events/{eid}/register", headers=student).get_json()["payment"]["id"] == "order_ABC"

    url = f"/api/events/{eid}/pay/verify"
    # the mock signature must NOT work once real keys are set
    assert client.post(url, json={"order_id": "order_ABC", "payment_id": "pay_1", "signature": "mock-paid"}, headers=student).status_code == 400
    good = hmac.new(b"secret123", b"order_ABC|pay_1", hashlib.sha256).hexdigest()
    r = client.post(url, json={"order_id": "order_ABC", "payment_id": "pay_1", "signature": good}, headers=student)
    assert r.status_code == 200 and r.get_json()["registration"]["status"] == "registered"