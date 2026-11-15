import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from .extensions import db
from .models import User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SIGNUP_ROLES = ("student", "organizer")  # admins are created manually, never via signup


def _error(message, status=400):
    return jsonify({"error": message}), status


@bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "student")

    if not name:
        return _error("Enter your name.")
    if not EMAIL_RE.match(email):
        return _error("Enter a valid email address.")
    if len(password) < 8:
        return _error("Password must be at least 8 characters.")
    if role not in SIGNUP_ROLES:
        return _error("Role must be student or organizer.")
    if User.query.filter_by(email=email).first():
        return _error("An account with this email already exists.", 409)

    user = User(
        name=name,
        email=email,
        role=role,
        country_code=(data.get("country_code") or "").upper()[:2] or None,
        city=data.get("city"),
        timezone=data.get("timezone"),
        language=data.get("language", "en"),
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"user": user.to_dict(), "access_token": token}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return _error("Email or password is incorrect.", 401)

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"user": user.to_dict(), "access_token": token})


@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return _error("User not found.", 404)
    return jsonify({"user": user.to_dict()})