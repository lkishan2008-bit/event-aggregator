import re

import pytest

from app import create_app
from app.extensions import db
from app.models import User
from config import TestConfig

STRONG = "Secret@123"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        admin = User(name="Admin", email="admin@x.co", role="admin", email_verified=True)
        admin.set_password("Admin@12345")
        db.session.add(admin)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def last_code(app, email):
    """Read the most recent OTP emailed to this address (tests keep emails in memory)."""
    mails = [m for m in app.extensions.get("outbox", []) if m["to"] == email]
    return re.search(r"\b(\d{6})\b", mails[-1]["subject"]).group(1)


class Auth:
    def __init__(self, app, client):
        self.app, self.client = app, client

    def _finish(self, email, purpose):
        r = self.client.post("/api/auth/verify-otp", json={"email": email, "purpose": purpose, "code": last_code(self.app, email)})
        assert r.status_code == 200, r.get_json()
        return {"Authorization": f"Bearer {r.get_json()['access_token']}"}

    def signup(self, email, role="student", password=STRONG):
        r = self.client.post("/api/auth/register", json={"name": "U", "email": email, "password": password, "role": role})
        assert r.status_code == 201, r.get_json()
        return self._finish(email, "signup")

    def login(self, email, password):
        r = self.client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.get_json()
        return self._finish(email, r.get_json()["purpose"])


@pytest.fixture
def auth(app, client):
    return Auth(app, client)