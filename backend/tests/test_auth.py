import pytest

from app import create_app
from app.extensions import db
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_register_login_me(client):
    r = client.post("/api/auth/register", json={
        "name": "Leo", "email": "Leo@Example.com", "password": "secret123",
        "country_code": "in", "city": "Bengaluru", "timezone": "Asia/Kolkata",
    })
    assert r.status_code == 201
    assert r.get_json()["user"]["country_code"] == "IN"

    r = client.post("/api/auth/login", json={"email": "leo@example.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.get_json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.get_json()["user"]["email"] == "leo@example.com"


def test_duplicate_and_bad_input(client):
    body = {"name": "A", "email": "a@b.co", "password": "secret123"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json=body).status_code == 409
    assert client.post("/api/auth/register", json={**body, "email": "x@y.co", "password": "short"}).status_code == 400
    assert client.post("/api/auth/register", json={**body, "email": "z@y.co", "role": "admin"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "a@b.co", "password": "wrong"}).status_code == 401