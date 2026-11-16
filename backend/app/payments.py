"""Razorpay payments for paid tickets.

Flow: Flask creates an order -> the browser opens Razorpay Checkout -> the student pays ->
Razorpay returns (order_id, payment_id, signature) -> Flask checks the signature with the
secret key. Only a valid signature turns the registration into a confirmed ticket.

Without Razorpay keys (local demo) a fake "mock" order is used so the flow can still be shown.
"""
import base64
import hashlib
import hmac
import json
import secrets
import urllib.request

from flask import current_app

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"
MOCK_SIGNATURE = "mock-paid"


def is_mock():
    cfg = current_app.config
    return not (cfg.get("RAZORPAY_KEY_ID") and cfg.get("RAZORPAY_KEY_SECRET"))


def create_order(amount_paise, currency, receipt):
    """Create a payment order. Returns {"id", "amount", "currency", "key_id", "mock"}."""
    if is_mock():
        return {"id": f"order_mock_{secrets.token_hex(8)}", "amount": amount_paise, "currency": currency, "key_id": None, "mock": True}

    cfg = current_app.config
    auth = base64.b64encode(f"{cfg['RAZORPAY_KEY_ID']}:{cfg['RAZORPAY_KEY_SECRET']}".encode()).decode()
    body = json.dumps({"amount": amount_paise, "currency": currency, "receipt": receipt}).encode()
    req = urllib.request.Request(
        RAZORPAY_ORDERS_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        order = json.loads(res.read())
    return {"id": order["id"], "amount": order["amount"], "currency": order["currency"], "key_id": cfg["RAZORPAY_KEY_ID"], "mock": False}


def signature_is_valid(order_id, payment_id, signature):
    """Razorpay signs "order_id|payment_id" with our secret key (HMAC-SHA256)."""
    if is_mock():
        return order_id.startswith("order_mock_") and signature == MOCK_SIGNATURE
    secret = current_app.config["RAZORPAY_KEY_SECRET"].encode()
    expected = hmac.new(secret, f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")