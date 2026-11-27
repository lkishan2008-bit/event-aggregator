"""Add sample LOCAL festivals, temple fairs, markets and community events.

Run after seed.py, from the backend folder:   python seed_local.py
Safe to run again: it skips anything that already exists.
Dates are SAMPLE dates relative to today, for demos only.
"""
from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import Event, Venue
from app.utils import utcnow_naive
from seed import IST_OFFSET, get_or_create_user

LOCAL_ORGANIZERS = {
    "blrcommunity": "Bengaluru Community Events",
    "mysurucommunity": "Mysuru Community Events",
}

# (title, category, days from now, local hour, duration hrs, price, organizer, venue, address, city, description)
LOCAL_EVENTS = [
    ("Kadlekai Parishe (Groundnut Fair)", "festival", 3, 10, 12, 0, "blrcommunity",
     "Bull Temple Grounds", "Bull Temple Road, Basavanagudi", "Bengaluru",
     "Traditional groundnut fair near the Bull Temple. Farmers sell fresh groundnuts, with street food, toys and local crafts. Free entry, family friendly."),
    ("Bengaluru Karaga Utsava", "festival", 10, 20, 8, 0, "blrcommunity",
     "Sri Dharmaraya Swamy Temple", "Nagarathpete, Old Bengaluru", "Bengaluru",
     "One of the city's oldest festivals. The night-time Karaga procession winds through the old city lanes with music and lights."),
    ("Banashankari Temple Jatre", "temple", 5, 8, 10, 0, "blrcommunity",
     "Banashankari Amma Temple", "Kanakapura Road, Banashankari", "Bengaluru",
     "Annual temple fair with the chariot procession, devotional music, stalls and local food."),
    ("Sunday Flea Market", "market", 2, 9, 6, 0, "blrcommunity",
     "Jayanagar 4th Block Complex", "Jayanagar 4th Block", "Bengaluru",
     "Weekly flea market with second-hand books, clothes, handicrafts and home-made snacks from local sellers."),
    ("Organic Farmers Market", "market", 4, 7, 4, 0, "blrcommunity",
     "Cubbon Park Bandstand", "Kasturba Road", "Bengaluru",
     "Fresh vegetables, millets, honey and cold-pressed oils straight from farmers around Bengaluru."),
    ("Weekend Handloom Mela", "market", 11, 11, 8, 0, "blrcommunity",
     "Chitrakala Parishath", "Kumarakrupa Road", "Bengaluru",
     "Handloom sarees, Ilkal and Mysore silk, and handicrafts from weaver groups across Karnataka."),
    ("Ganesh Utsava Cultural Night", "festival", 14, 18, 4, 0, "blrcommunity",
     "National College Grounds", "Basavanagudi", "Bengaluru",
     "An evening of classical and folk music during Ganesh Utsava. Free entry, seating is first come, first served."),
    ("Kannada Rajyotsava Folk Evening", "festival", 8, 17, 3, 0, "blrcommunity",
     "Ravindra Kalakshetra", "JC Road", "Bengaluru",
     "Folk dance and music from across Karnataka: Dollu Kunitha, Yakshagana excerpts and Janapada songs."),
    ("Ulsoor Lake Clean-up Drive", "community", 6, 7, 3, 0, "blrcommunity",
     "Ulsoor Lake Main Gate", "Ulsoor", "Bengaluru",
     "Join neighbours to clean the lake shore. Gloves and bags provided. Open to families and volunteers of all ages."),
    ("Mysuru Dasara Palace Illumination", "festival", 16, 19, 3, 0, "mysurucommunity",
     "Mysuru Palace", "Sayyaji Rao Road", "Mysuru",
     "The palace lit up with thousands of bulbs during Dasara, with cultural programmes in the forecourt."),
    ("Devaraja Market Heritage Walk", "market", 9, 8, 2, 99, "mysurucommunity",
     "Devaraja Market", "Sayyaji Rao Road", "Mysuru",
     "Guided morning walk through the historic Devaraja Market: flowers, spices, incense and local stories."),
]


def run():
    app = create_app()
    with app.app_context():
        db.create_all()
        organizers = {
            key: get_or_create_user(name, f"{key}@example.com", "Organizer@123", "organizer")
            for key, name in LOCAL_ORGANIZERS.items()
        }
        db.session.commit()

        today = utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)
        for title, category, days, hour, hours, price, org, venue_name, address, city, description in LOCAL_EVENTS:
            if Event.query.filter_by(title=title).first():
                continue
            start_utc = today + timedelta(days=days, hours=hour) - IST_OFFSET
            db.session.add(Event(
                organizer_id=organizers[org].id,
                venue=Venue(name=venue_name, address=address, city=city, country_code="IN"),
                title=title, category=category, description=description,
                start_utc=start_utc, end_utc=start_utc + timedelta(hours=hours),
                timezone="Asia/Kolkata", price_amount=price, currency="INR",
                is_free=(price == 0), status="approved",
            ))
            print(f"created event: {title}")
        db.session.commit()
        print("Local seed done.")


if __name__ == "__main__":
    run()
