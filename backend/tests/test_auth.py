from datetime import timedelta

from app.extensions import db
from app.models import OtpCode
from conftest import STRONG, last_code


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_signup_needs_otp_then_login_needs_otp(client, app, auth):
    r = client.post("/api/auth/register", json={
        "name": "Leo", "email": "Leo@Example.com", "password": STRONG,
        "country_code": "in", "city": "Bengaluru", "timezone": "Asia/Kolkata",
    })
    assert r.status_code == 201
    body = r.get_json()
    assert body == {"otp_required": True, "purpose": "signup", "email": "leo@example.com"}
    assert "access_token" not in body          # no login until the code is entered

    code = last_code(app, "leo@example.com")
    r = client.post("/api/auth/verify-otp", json={"email": "leo@example.com", "purpose": "signup", "code": code})
    assert r.status_code == 200
    token = r.get_json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).get_json()["user"]
    assert me["email_verified"] and me["country_code"] == "IN"

    # login = password + new code
    r = client.post("/api/auth/login", json={"email": "leo@example.com", "password": STRONG})
    assert r.get_json() == {"otp_required": True, "purpose": "login", "email": "leo@example.com"}
    assert auth.login("leo@example.com", STRONG)  # completes with the emailed code


def test_password_rules(client):
    base = {"name": "A", "email": "a@b.co"}
    for weak, missing in [
        ("Ab1!", "at least 8 characters"),
        ("secret@123", "an uppercase letter"),
        ("SECRET@123", "a lowercase letter"),
        ("Secret@abc", "a number"),
        ("Secret1234", "a symbol"),
    ]:
        r = client.post("/api/auth/register", json={**base, "password": weak})
        assert r.status_code == 400 and missing in r.get_json()["error"], weak


def test_wrong_expired_and_too_many_codes(client, app, auth):
    client.post("/api/auth/register", json={"name": "A", "email": "a@b.co", "password": STRONG})
    good = last_code(app, "a@b.co")
    wrong = "000000" if good != "000000" else "111111"

    r = client.post("/api/auth/verify-otp", json={"email": "a@b.co", "purpose": "signup", "code": wrong})
    assert r.status_code == 400 and "4 attempts left" in r.get_json()["error"]
    assert client.post("/api/auth/verify-otp", json={"email": "a@b.co", "purpose": "signup", "code": "12ab"}).status_code == 400

    for _ in range(4):
        client.post("/api/auth/verify-otp", json={"email": "a@b.co", "purpose": "signup", "code": wrong})
    r = client.post("/api/auth/verify-otp", json={"email": "a@b.co", "purpose": "signup", "code": good})
    assert "Too many wrong attempts" in r.get_json()["error"]   # locked even with the right code

    # a fresh code works, but not after it expires
    with app.app_context():
        for otp in OtpCode.query.all():
            otp.created_at -= timedelta(minutes=2)
        db.session.commit()
    assert client.post("/api/auth/resend-otp", json={"email": "a@b.co", "purpose": "signup"}).status_code == 200
    with app.app_context():
        for otp in OtpCode.query.filter_by(used=False):
            otp.expires_at -= timedelta(minutes=11)
        db.session.commit()
    r = client.post("/api/auth/verify-otp", json={"email": "a@b.co", "purpose": "signup", "code": last_code(app, "a@b.co")})
    assert "expired" in r.get_json()["error"]


def test_resend_cooldown_and_unverified_login(client, app):
    client.post("/api/auth/register", json={"name": "A", "email": "a@b.co", "password": STRONG})
    r = client.post("/api/auth/resend-otp", json={"email": "a@b.co", "purpose": "signup"})
    assert r.status_code == 429

    # logging in before verifying sends you to finish signup, not a login code
    r = client.post("/api/auth/login", json={"email": "a@b.co", "password": STRONG})
    assert r.get_json()["purpose"] == "signup"

    # unknown emails get the same "sent" answer
    assert client.post("/api/auth/resend-otp", json={"email": "nobody@x.co", "purpose": "login"}).get_json() == {"sent": True}


def test_duplicate_and_bad_login(client, auth):
    auth.signup("a@b.co")
    r = client.post("/api/auth/register", json={"name": "A", "email": "a@b.co", "password": STRONG})
    assert r.status_code == 409
    assert client.post("/api/auth/login", json={"email": "a@b.co", "password": "Wrong@123"}).status_code == 401
    r = client.post("/api/auth/register", json={"name": "A", "email": "z@y.co", "password": STRONG, "role": "admin"})
    assert r.status_code == 400
    

def test_update_profile(client, auth):
    h = auth.signup("p@x.co")
    r = client.patch("/api/auth/me", json={"name": "Kishan L", "city": "Bengaluru", "country_code": "in"}, headers=h)
    assert r.status_code == 200
    u = r.get_json()["user"]
    assert (u["name"], u["city"], u["country_code"]) == ("Kishan L", "Bengaluru", "IN")
    assert client.patch("/api/auth/me", json={"name": ""}, headers=h).status_code == 400
    assert client.patch("/api/auth/me", json={"country_code": "IND"}, headers=h).status_code == 400
    assert client.patch("/api/auth/me", json={"name": "X"}).status_code == 401