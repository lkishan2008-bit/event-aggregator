import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

from .extensions import db
from .models import User
from .otp import issue_otp, seconds_until_resend, verify_otp

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SIGNUP_ROLES = ("student", "organizer")  # admins are created manually, never via signup


def _error(message, status=400):
    return jsonify({"error": message}), status


def password_problems(password):
    """List what's missing from a password. Empty list = strong enough."""
    problems = []
    if len(password) < 8:
        problems.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        problems.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        problems.append("a lowercase letter")
    if not re.search(r"\d", password):
        problems.append("a number")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a symbol")
    return problems


def _token_response(user):
    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"user": user.to_dict(), "access_token": token})


@bp.post("/register")
def register():
    """Step 1 of signup: create the account (unverified) and email a code."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role", "student")

    if not name:
        return _error("Enter your name.")
    if not EMAIL_RE.match(email):
        return _error("Enter a valid email address.")
    problems = password_problems(password)
    if problems:
        return _error("Password needs " + ", ".join(problems) + ".")
    if role not in SIGNUP_ROLES:
        return _error("Role must be student or organizer.")

    user = User.query.filter_by(email=email).first()
    if user and user.email_verified:
        return _error("An account with this email already exists.", 409)

    if user:
        # signed up before but never verified: update details and send a fresh code
        user.name, user.role = name, role
    else:
        user = User(name=name, email=email, role=role, email_verified=False)
        db.session.add(user)
    user.country_code = (data.get("country_code") or "").upper()[:2] or None
    user.city = data.get("city")
    user.timezone = data.get("timezone")
    user.language = data.get("language", "en")
    user.set_password(password)
    db.session.commit()

    issue_otp(user, "signup")
    return jsonify({"otp_required": True, "purpose": "signup", "email": email}), 201


@bp.post("/login")
def login():
    """Step 1 of login: check the password, then email a code."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return _error("Email or password is incorrect.", 401)

    purpose = "login" if user.email_verified else "signup"
    wait = seconds_until_resend(user, purpose)
    if not wait:
        issue_otp(user, purpose)
    return jsonify({"otp_required": True, "purpose": purpose, "email": email})


@bp.post("/verify-otp")
def verify():
    """Step 2: check the emailed code and log the user in."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    purpose = data.get("purpose")

    if purpose not in ("signup", "login"):
        return _error("purpose must be signup or login.")
    if not re.fullmatch(r"\d{6}", code):
        return _error("Enter the 6-digit code from your email.")

    user = User.query.filter_by(email=email).first()
    if not user:
        return _error("No active code. Request a new one.")

    problem = verify_otp(user, purpose, code)
    if problem:
        return _error(problem)

    if purpose == "signup":
        user.email_verified = True
        db.session.commit()
    return _token_response(user)


@bp.post("/resend-otp")
def resend():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    purpose = data.get("purpose")
    if purpose not in ("signup", "login"):
        return _error("purpose must be signup or login.")

    user = User.query.filter_by(email=email).first()
    # same answer whether or not the account exists, so emails can't be probed
    if user and (purpose == "login") == bool(user.email_verified):
        wait = seconds_until_resend(user, purpose)
        if wait:
            return _error(f"Wait {wait} seconds before requesting another code.", 429)
        issue_otp(user, purpose)
    return jsonify({"sent": True})


@bp.patch("/me")
@jwt_required()
def update_me():
    """Edit your own profile: name, city, country."""
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return _error("User not found.", 404)
    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name or len(name) > 120:
            return _error("Name must be 1 to 120 characters.")
        user.name = name
    if "city" in data:
        city = (data.get("city") or "").strip()
        if len(city) > 120:
            return _error("City name is too long.")
        user.city = city or None
    if "country_code" in data:
        cc = (data.get("country_code") or "").strip().upper()
        if cc and (len(cc) != 2 or not cc.isalpha()):
            return _error("Country must be a 2-letter code, e.g. IN or US.")
        user.country_code = cc or None

    db.session.commit()
    return jsonify({"user": user.to_dict()})
@bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return _error("User not found.", 404)
    return jsonify({"user": user.to_dict()})

@bp.post("/forgot")
def forgot_password():
    """Body: {"email"}. Emails a reset code. Same answer whether or not the account exists (no account fishing)."""
    email = str((request.get_json(silent=True) or {}).get("email", "")).strip().lower()
    user = User.query.filter_by(email=email).first()
    if user:
        wait = seconds_until_resend(user, "reset")
        if wait:
            return _error(f"Wait {wait} seconds before asking for a new code.", 429)
        issue_otp(user, "reset")
    return jsonify({"sent": True, "email": email})


@bp.post("/reset")
def reset_password():
    """Body: {"email", "code", "password"}. Sets a new password if the emailed code is right."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", ""))
    user = User.query.filter_by(email=email).first()
    if not user:
        return _error("Wrong code or email.")
    problems = password_problems(password)
    if problems:
        return _error("Password needs " + ", ".join(problems) + ".")
    problem = verify_otp(user, "reset", code)
    if problem:
        return _error(problem)
    user.set_password(password)
    user.email_verified = True  # they proved they own the email
    db.session.commit()
    return jsonify({"reset": True})