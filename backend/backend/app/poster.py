"""Poster to listing: read an event poster (photo) and pre-fill the submit form.

1. OCR: Amazon Textract (AWS) turns the poster image into lines of text.
   Organizers can also paste the text instead (e.g. an Instagram caption).
2. Parsing: simple rules pick out the title, date, time, venue, price, category and link.
The organizer always checks the pre-filled form before submitting.
"""
import base64
import re
from datetime import date

from flask import Blueprint, current_app, jsonify, request

from .utils import error, roles_required

bp = Blueprint("poster", __name__, url_prefix="/api/organizer")

MAX_IMAGE_BYTES = 5 * 1024 * 1024

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
MONTH_RE = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
ORD = r"(?:st|nd|rd|th)?"

CATEGORY_WORDS = [
    ("hackathon", ("hackathon", "codeathon", "ideathon", "hack ", "coding contest", "competitive programming")),
    ("workshop", ("workshop", "bootcamp", "masterclass", "hands-on", "hands on")),
    ("conference", ("conference", "summit", "symposium", "conclave")),
    ("sports", ("tournament", "cricket", "football", "marathon", "sports", "basketball")),
    ("fest", ("fest", "festival", "pro-show", "pro show")),
    ("cultural", ("cultural", "dance", "music night", "concert")),
    ("meetup", ("meetup", "meet-up", "networking", "talk", "webinar")),
]
VENUE_RE = re.compile(r"(?<![\w-])(auditorium|hall|campus|college|university|institute|grounds?|lab|block|"
                      r"center|centre|stadium|theatre|theater|amphitheatre|park)\b", re.I)
CITIES = {"bengaluru": "Bengaluru", "bangalore": "Bengaluru", "mumbai": "Mumbai", "delhi": "Delhi",
          "chennai": "Chennai", "hyderabad": "Hyderabad", "pune": "Pune", "kolkata": "Kolkata", "mysuru": "Mysuru", "mysore": "Mysuru"}
SKIP_TITLE = re.compile(r"\b(presents?|invites?|proudly|organi[sz]ed by|in association|in collaboration|welcome|department of)\b", re.I)
URL_RE = re.compile(r"(https?://\S+|www\.\S+|bit\.ly/\S+|forms\.gle/\S+|lu\.ma/\S+|unstop\.com/\S+)", re.I)
PRICE_RE = re.compile(r"(?:\u20b9|\brs\.?|\binr)\s*(\d[\d,]*)", re.I)
FEE_RE = re.compile(r"\b(?:entry|registration|reg\.?|fee|fees|ticket|tickets)\b[^\d\n]{0,20}(\d[\d,]*)", re.I)


def _year_for(month, day, today):
    """Posters often skip the year: use this year, or next year if that date has passed."""
    try:
        d = date(today.year, month, day)
    except ValueError:
        return None
    return today.year if d >= today else today.year + 1


def find_date(text, today):
    t = text.lower()
    m = re.search(rf"\b(\d{{1,2}}){ORD}\s*(?:(?:-|to|&|and)\s*\d{{1,2}}{ORD}\s*)?(?:of\s+)?{MONTH_RE}\b[,.]?\s*(\d{{4}})?", t)
    if m:
        day, month, year = int(m.group(1)), MONTHS[m.group(2)], m.group(3)
    else:
        m = re.search(rf"\b{MONTH_RE}\s+(\d{{1,2}}){ORD}\b,?\s*(\d{{4}})?", t)
        if m:
            month, day, year = MONTHS[m.group(1)], int(m.group(2)), m.group(3)
        else:
            m = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b", t)  # 12/03/2026 (day first, as in India)
            if not m:
                return None
            day, month, year = int(m.group(1)), int(m.group(2)), m.group(3)
            if len(year) == 2:
                year = "20" + year
    year = int(year) if year else _year_for(month, day, today)
    try:
        return date(year, month, day).isoformat() if year else None
    except ValueError:
        return None


def _to_24h(hour, minute, meridiem):
    hour, minute = int(hour), int(minute or 0)
    meridiem = (meridiem or "").replace(".", "").lower()
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def find_times(text):
    """Returns (start, end) as "HH:MM" strings (either can be None)."""
    t = text.lower()
    rng = re.search(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\s*(?:-|to|till|until)\s*(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", t)
    if rng:
        end_mer = rng.group(6)
        start_mer = rng.group(3)
        if not start_mer:  # "10 - 5 pm": start is am if pm would come after the end
            start_mer = end_mer
            s, e = _to_24h(rng.group(1), rng.group(2), start_mer), _to_24h(rng.group(4), rng.group(5), end_mer)
            if s and e and s > e:
                start_mer = "am"
        return _to_24h(rng.group(1), rng.group(2), start_mer), _to_24h(rng.group(4), rng.group(5), end_mer)
    single = re.search(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", t)
    if single:
        return _to_24h(single.group(1), single.group(2), single.group(3)), None
    h24 = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", t)
    if h24:
        return f"{int(h24.group(1)):02d}:{h24.group(2)}", None
    return None, None


def find_price(text):
    if PRICE_RE.search(text):
        return int(PRICE_RE.search(text).group(1).replace(",", ""))
    fee = FEE_RE.search(text)
    if fee:
        return int(fee.group(1).replace(",", ""))
    if re.search(r"\bfree\b", text, re.I):
        return 0
    return None


def find_category(text):
    t = f" {text.lower()} "
    for category, words in CATEGORY_WORDS:
        if any(w in t for w in words):
            return category
    return None


def _is_meta_line(line):
    """Lines that are dates, times, prices, links or labels - not the title."""
    low = line.lower()
    return bool(
        URL_RE.search(line) or PRICE_RE.search(line) or re.search(MONTH_RE + r"\b", low) and re.search(r"\d", low)
        or re.search(r"\d{1,2}\s*(am|pm)", low) or re.match(r"^(venue|date|time|when|where|contact|call|register|entry|fee)\b", low)
        or len(re.sub(r"[^a-z0-9]", "", low)) < 3
    )


def extract_fields(text, today=None):
    today = today or date.today()
    lines = [re.sub(r"\s+", " ", ln).strip(" |:-") for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    fields = {}

    title = next((ln for ln in lines[:6] if not _is_meta_line(ln) and not SKIP_TITLE.search(ln)), None)
    if title:
        fields["title"] = title[:200]

    category = find_category(text)
    if category:
        fields["category"] = category

    day = find_date(text, today)
    if day:
        fields["date"] = day
    start, end = find_times(text)
    if start:
        fields["start"] = start
    if end:
        fields["end"] = end

    price = find_price(text)
    if price is not None:
        fields["price"] = price

    venue = None
    for ln in lines:
        m = re.match(r"^(?:venue|where|location)\s*[:\-]?\s*(.+)$", ln, re.I)
        if m:
            venue = m.group(1)
            break
    if not venue:
        venue = next((ln for ln in lines if ln != title and VENUE_RE.search(ln) and not ln.endswith("!")
                      and not SKIP_TITLE.search(ln)), None)
    if venue:
        fields["venue"] = venue[:200]

    low = text.lower()
    city = next((name for key, name in CITIES.items() if key in low), None)
    if city:
        fields["city"] = city

    url = URL_RE.search(text)
    if url:
        link = url.group(1).rstrip(".,)")
        fields["link"] = link if link.lower().startswith("http") else f"https://{link}"

    rest = [ln for ln in lines if ln != title]
    if rest:
        fields["description"] = "\n".join(rest)[:2000]
    return fields


def ocr_image(image_bytes):
    """Poster photo -> text, using Amazon Textract (same AWS keys as SES; needs Textract permission)."""
    import boto3

    client = boto3.client("textract", region_name=current_app.config["AWS_REGION"])
    res = client.detect_document_text(Document={"Bytes": image_bytes})
    return "\n".join(b["Text"] for b in res.get("Blocks", []) if b.get("BlockType") == "LINE")


@bp.post("/poster/scan")
@roles_required("organizer", "admin")
def scan_poster():
    """Body: {"image_base64": "..."} (a JPEG/PNG photo) or {"text": "..."}. Returns form fields to pre-fill."""
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()

    if not text:
        raw = str(data.get("image_base64") or "")
        if not raw:
            return error("Upload a poster photo or paste the poster text.")
        if "," in raw[:100]:
            raw = raw.split(",", 1)[1]  # strip "data:image/jpeg;base64,"
        try:
            image = base64.b64decode(raw, validate=True)
        except ValueError:
            return error("That image couldn't be read. Try a JPG or PNG.")
        if len(image) > MAX_IMAGE_BYTES:
            return error("Image is too large (max 5 MB).")
        try:
            text = ocr_image(image)
        except Exception as exc:
            current_app.logger.warning("poster OCR failed: %s", exc)
            return error("Poster reading isn't available right now. Paste the poster text instead.", 503)
        if not text.strip():
            return error("No text found on that image. Try a clearer photo.", 422)

    fields = extract_fields(text)
    return jsonify({"fields": fields, "text": text})