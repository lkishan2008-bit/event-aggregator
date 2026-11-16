import base64
from datetime import date

from app.poster import extract_fields

TODAY = date(2026, 11, 16)

HACK_POSTER = """RV College of Engineering presents
HACKRV 4.0
24-Hour National Level Hackathon
12th - 13th March 2027
9:00 AM - 9:00 AM
Venue: RVCE Main Auditorium, Mysore Road, Bengaluru
Registration fee: Rs. 300 per team
Register at bit.ly/hackrv4
"""

FEST_CAPTION = """Unwind Fest
The biggest inter-college cultural festival is back!
Dec 5 | 5 pm onwards
Christ University Main Campus, Bangalore
Entry: \u20b9199
"""

WORKSHOP = """Intro to Flutter
A hands-on workshop for beginners
Date: 20/01/2027  Time: 10 - 1 pm
Seminar Hall 2, PES University
Free for all students
https://forms.gle/abc123
"""


def test_extract_hackathon_poster():
    f = extract_fields(HACK_POSTER, TODAY)
    assert f["title"] == "HACKRV 4.0"
    assert f["category"] == "hackathon"
    assert f["date"] == "2027-03-12"
    assert f["start"] == "09:00"
    assert f["price"] == 300
    assert f["venue"].startswith("RVCE Main Auditorium")
    assert f["city"] == "Bengaluru"
    assert f["link"] == "https://bit.ly/hackrv4"


def test_extract_fest_caption_without_year():
    f = extract_fields(FEST_CAPTION, TODAY)
    assert f["title"] == "Unwind Fest"
    assert f["category"] == "fest"
    assert f["date"] == "2026-12-05"          # no year on the poster: next upcoming 5 Dec
    assert f["start"] == "17:00"
    assert f["price"] == 199
    assert f["venue"] == "Christ University Main Campus, Bangalore"


def test_extract_workshop_free_and_range():
    f = extract_fields(WORKSHOP, TODAY)
    assert f["title"] == "Intro to Flutter"
    assert f["category"] == "workshop"
    assert f["date"] == "2027-01-20"
    assert (f["start"], f["end"]) == ("10:00", "13:00")
    assert f["price"] == 0
    assert f["link"] == "https://forms.gle/abc123"


def test_scan_endpoint_text_and_image(client, auth, monkeypatch):
    org = auth.signup("o@x.co", "organizer")
    student = auth.signup("s@x.co")
    url = "/api/organizer/poster/scan"

    assert client.post(url, json={"text": FEST_CAPTION}, headers=student).status_code == 403
    r = client.post(url, json={"text": FEST_CAPTION}, headers=org)
    assert r.status_code == 200 and r.get_json()["fields"]["price"] == 199

    # image path: Textract is replaced by a fake that returns the poster text
    monkeypatch.setattr("app.poster.ocr_image", lambda image: HACK_POSTER)
    img = "data:image/png;base64," + base64.b64encode(b"fake-png-bytes").decode()
    r = client.post(url, json={"image_base64": img}, headers=org)
    assert r.status_code == 200 and r.get_json()["fields"]["title"] == "HACKRV 4.0"

    def broken(image):
        raise RuntimeError("AccessDenied")
    monkeypatch.setattr("app.poster.ocr_image", broken)
    assert client.post(url, json={"image_base64": img}, headers=org).status_code == 503
    assert client.post(url, json={}, headers=org).status_code == 400