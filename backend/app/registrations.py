from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from .email import send_email
from .events import _going_counts, serialize_event
from .extensions import db
from .models import Event, Registration, User
from .payments import create_order, signature_is_valid
from .utils import error, to_iso_utc, utcnow_naive

bp = Blueprint("registrations", __name__, url_prefix="/api")


def serialize_registration(reg, include_event=True):
    data = {
        "id": reg.id,
        "status": reg.status,
        "qr_token": reg.qr_token if reg.status == "registered" else None,  # no QR until paid
        "amount_paid": float(reg.amount_paid or 0),
        "checked_in_at": to_iso_utc(reg.checked_in_at),
        "created_at": to_iso_utc(reg.created_at),
    }
    if include_event:
        event = db.session.get(Event, reg.event_id)
        data["event"] = serialize_event(event, _going_counts([event.id]).get(event.id, 0))
    return data


def _send_confirmation(user_id, event):
    """Email the 'you're going' confirmation. A failed email never breaks the registration."""
    user = db.session.get(User, user_id)
    when = event.start_utc.strftime("%d %b %Y, %H:%M UTC")
    where = f"{event.venue.name}, {event.venue.city}" if event.venue else "See the event page"
    text = (
        f"Hi {user.name},\n\nYou're registered for {event.title}.\n\n"
        f"When: {when}\nWhere: {where}\n\n"
        "Open the Passes tab in the app and show your QR code at the entrance.\n"
    )
    try:
        send_email(user.email, f"You're going: {event.title}", text)
    except Exception as exc:  # e.g. SES sandbox refuses an unverified address
        current_app.logger.warning("confirmation email failed: %s", exc)


def _event_is_open(event):
    if not event or event.status != "approved":
        return False
    now = utcnow_naive()
    end = event.end_utc or event.start_utc
    return end >= now


def _is_paid(event):
    return not event.is_free and Decimal(event.price_amount or 0) > 0


@bp.post("/events/<int:event_id>/register")
@jwt_required()
def register(event_id):
    """Register the logged-in user for an event.

    Free event: confirmed at once (201) and the QR pass is ready.
    Paid event: a pending registration + a payment order is returned (200); the ticket is
    confirmed only after POST /events/<id>/pay/verify succeeds.
    """
    event = db.session.get(Event, event_id)
    if not _event_is_open(event):
        return error("This event isn't open for registration.", 404 if not event else 400)

    user_id = int(get_jwt_identity())
    reg = Registration.query.filter_by(user_id=user_id, event_id=event_id).first()
    if reg and reg.status == "registered":
        return jsonify({"registration": serialize_registration(reg)})  # already going: same pass
    if not reg:
        reg = Registration(user_id=user_id, event_id=event_id)
        db.session.add(reg)

    if _is_paid(event):
        amount_paise = int(Decimal(event.price_amount) * 100)
        try:
            order = create_order(amount_paise, event.currency, receipt=f"ev{event.id}-u{user_id}")
        except Exception as exc:
            current_app.logger.error("razorpay order failed: %s", exc)
            return error("Payments are unavailable right now. Try again in a minute.", 502)
        reg.status = "pending_payment"
        reg.payment_order_id = order["id"]
        db.session.commit()
        user = db.session.get(User, user_id)
        return jsonify({
            "registration": serialize_registration(reg),
            "payment": {**order, "event_title": event.title, "name": user.name, "email": user.email},
        })

    reg.status = "registered"
    db.session.commit()
    _send_confirmation(user_id, event)
    return jsonify({"registration": serialize_registration(reg)}), 201


@bp.post("/events/<int:event_id>/pay/verify")
@jwt_required()
def verify_payment(event_id):
    """Body: {order_id, payment_id, signature} from Razorpay Checkout. Confirms the ticket if the signature is real."""
    data = request.get_json(silent=True) or {}
    order_id, payment_id, signature = (str(data.get(k, "")) for k in ("order_id", "payment_id", "signature"))
    reg = Registration.query.filter_by(user_id=int(get_jwt_identity()), event_id=event_id, payment_order_id=order_id).first()
    if not reg:
        return error("Payment not found.", 404)
    if reg.status == "registered":
        return jsonify({"registration": serialize_registration(reg)})  # already confirmed
    if not signature_is_valid(order_id, payment_id, signature):
        return error("Payment couldn't be verified.", 400)

    event = db.session.get(Event, event_id)
    reg.status = "registered"
    reg.payment_id = payment_id or None
    reg.amount_paid = event.price_amount
    db.session.commit()
    _send_confirmation(reg.user_id, event)
    return jsonify({"registration": serialize_registration(reg)})


@bp.delete("/events/<int:event_id>/register")
@jwt_required()
def cancel(event_id):
    reg = Registration.query.filter_by(user_id=int(get_jwt_identity()), event_id=event_id).first()
    if not reg or reg.status != "registered":
        return error("You're not registered for this event.", 404)
    if reg.checked_in_at:
        return error("You've already checked in, so this can't be cancelled.", 409)
    if reg.payment_id:
        return error("Paid tickets can't be cancelled here. Contact the organizer for a refund.", 409)
    reg.status = "cancelled"
    db.session.commit()
    return jsonify({"registration": serialize_registration(reg)})


@bp.get("/events/<int:event_id>/my-registration")
@jwt_required()
def my_registration(event_id):
    reg = Registration.query.filter_by(user_id=int(get_jwt_identity()), event_id=event_id, status="registered").first()
    return jsonify({"registration": serialize_registration(reg, include_event=False) if reg else None})


@bp.get("/me/registrations")
@jwt_required()
def my_registrations():
    regs = Registration.query.filter_by(user_id=int(get_jwt_identity()), status="registered").all()
    items = [serialize_registration(r) for r in regs]
    items.sort(key=lambda r: r["event"]["start_utc"])
    return jsonify({"registrations": items})