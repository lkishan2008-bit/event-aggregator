from datetime import datetime, timedelta, timezone


def test_sponsor_report_numbers(client, auth):
    admin = auth.login("admin@x.co", "Admin@12345")
    org = auth.signup("club@x.co", "organizer")
    other = auth.signup("other@x.co", "organizer")
    start = datetime.now(timezone.utc) + timedelta(days=2)
    body = {
        "title": "Paid Fest", "category": "fest", "start_utc": start.isoformat(), "end_utc": (start + timedelta(hours=5)).isoformat(),
        "timezone": "Asia/Kolkata", "price_amount": 100, "currency": "INR",
        "venue": {"name": "RVCE", "city": "Bengaluru", "country_code": "IN"},
    }
    eid = client.post("/api/events", json=body, headers=org).get_json()["event"]["id"]
    client.post(f"/api/admin/events/{eid}/approve", headers=admin)

    students = [auth.signup(e) for e in ("a@rvce.edu.in", "b@rvce.edu.in", "c@pes.edu", "d@gmail.com")]
    codes = []
    for s in students:
        order = client.post(f"/api/events/{eid}/register", headers=s).get_json()["payment"]
        reg = client.post(f"/api/events/{eid}/pay/verify", headers=s,
                          json={"order_id": order["id"], "payment_id": "pay_x", "signature": "mock-paid"}).get_json()["registration"]
        codes.append(reg["qr_token"])
    for code in codes[:3]:  # 3 of 4 came
        client.post(f"/api/organizer/events/{eid}/checkin", json={"code": code}, headers=org)

    url = f"/api/organizer/events/{eid}/report"
    assert client.get(url, headers=other).status_code == 404          # only the event's own organizer (or admin)
    assert client.get(url, headers=admin).status_code == 200
    r = client.get(url, headers=org).get_json()
    t = r["totals"]
    assert t["registered"] == 4 and t["checked_in"] == 3 and t["attendance_rate"] == 75
    assert t["paid_tickets"] == 4 and t["revenue"] == 400 and t["currency"] == "INR"
    assert r["institutions"][0] == {"name": "rvce.edu.in", "count": 2}
    assert {"name": "Personal email", "count": 1} in r["institutions"]
    assert sum(h["count"] for h in r["arrivals_by_hour"]) == 3
    assert sum(d["count"] for d in r["registrations_by_day"]) == 4