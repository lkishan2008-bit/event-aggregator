"""Database models.

Global-ready rules used everywhere:
- All datetimes are stored in UTC. Each event also stores its IANA timezone
  (e.g. "Asia/Kolkata", "Asia/Tokyo", "America/New_York") so the app can show
  local time.
- Prices are stored as a Decimal amount + ISO 4217 currency code ("INR", "USD", "JPY").
- Locations use ISO 3166 country codes ("IN", "US", "JP") + city + lat/lng.
"""
import secrets
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    ROLES = ("student", "organizer", "admin")

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

    country_code = db.Column(db.String(2))      # ISO 3166-1 alpha-2, e.g. "IN"
    city = db.Column(db.String(120))
    timezone = db.Column(db.String(64))         # IANA, e.g. "Asia/Kolkata"
    language = db.Column(db.String(10), default="en")
    email_verified = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "country_code": self.country_code,
            "city": self.city,
            "timezone": self.timezone,
            "language": self.language,
                        "email_verified": bool(self.email_verified),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Venue(db.Model):
    __tablename__ = "venues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(500))
    city = db.Column(db.String(120), nullable=False, index=True)
    country_code = db.Column(db.String(2), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class Event(db.Model):
    __tablename__ = "events"

    STATUSES = ("pending", "approved", "rejected", "cancelled", "completed")

    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id"))

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), index=True)    # fest, hackathon, workshop, meetup...

    start_utc = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    end_utc = db.Column(db.DateTime(timezone=True))
    timezone = db.Column(db.String(64), nullable=False)  # event's local IANA timezone

    price_amount = db.Column(db.Numeric(12, 2), default=0)
    currency = db.Column(db.String(3), default="INR")   # ISO 4217
    is_free = db.Column(db.Boolean, default=True, index=True)

    poster_url = db.Column(db.String(500))
    registration_url = db.Column(db.String(500))       # external booking link, if any
    source_url = db.Column(db.String(500))

    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organizer = db.relationship("User", backref="events")
    venue = db.relationship("Venue", backref="events")


class Registration(db.Model):
    __tablename__ = "registrations"
    __table_args__ = (db.UniqueConstraint("user_id", "event_id", name="uq_user_event"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    status = db.Column(db.String(20), default="registered")  # registered, cancelled
    qr_token = db.Column(db.String(64), unique=True, default=lambda: secrets.token_urlsafe(24))
    checked_in_at = db.Column(db.DateTime(timezone=True))   # set when QR is scanned at the gate
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    

class OtpCode(db.Model):
    """A one-time code emailed to the user. Only a hash of the code is stored."""
    __tablename__ = "otp_codes"

    PURPOSES = ("signup", "login")

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    purpose = db.Column(db.String(20), nullable=False)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)   # UTC
    attempts = db.Column(db.Integer, default=0, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)   # UTC