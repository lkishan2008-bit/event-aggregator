from datetime import datetime, timezone
from functools import wraps
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def error(message, status=400):
    return jsonify({"error": message}), status


def roles_required(*roles):
    """Allow the request only if the logged-in user has one of these roles."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            if get_jwt().get("role") not in roles:
                return error("You don't have permission to do this.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def parse_utc(value):
    """Parse an ISO 8601 datetime that includes a timezone ('Z' or '+05:30') and return it in UTC.

    Stored without tzinfo so SQLite and PostgreSQL behave the same; every stored value is UTC.
    """
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_iso_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="seconds") + "Z"


def utcnow_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def valid_timezone(name):
    if not name or not isinstance(name, str):
        return False
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False
        