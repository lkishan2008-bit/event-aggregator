"""Fill the local database with demo accounts and events.

Run from the backend folder:   python seed.py
Safe to run again: it skips anything that already exists.
"""
from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import Event, User, Venue
from app.utils import utcnow_naive

ACCOUNTS = [
    ("Admin", "admin@example.com", "admin12345", "admin"),
    ("RVCE Tech Club", "organizer@example.com", "organizer123", "organizer"),
    ("Demo Student", "student@example.com", "student123", "student"),
]

# (title, category, days from now, local hour, price, venue, city)
EVENTS = [
    ("HackRV 3.0", "hackathon", 6, 9, 0, "RVCE, Mysore Road", "Bengaluru"),
    ("Intro to CRISPR Workshop", "workshop", 5, 14, 0, "IISc, Malleshwaram", "Bengaluru"),
    ("BangPypers Monthly Meetup", "meetup", 7, 11, 0, "Koramangala", "Bengaluru"),
    ("8th Mile Cultural Fest", "fest", 12, 12, 199, "RVCE Main Grounds", "Bengaluru"),
    ("UI/UX Design Sprint", "workshop", 19, 10, 299, "PES University", "Bengaluru"),
]

IST_OFFSET = timedelta(hours=5, minutes=30)


def run():
    app = create_app()
    with app.app_context():
        db.create_all()

        users = {}
        for name, email, password, role in ACCOUNTS:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(name=name, email=email, role=role, country_code="IN",
                            city="Bengaluru", timezone="Asia/Kolkata")
                user.set_password(password)
                db.session.add(user)
                print(f"created {role}: {email} / {password}")
            users[role] = user
        db.session.commit()

        today = utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)
        for title, category, days, hour, price, venue_name, city in EVENTS:
            if Event.query.filter_by(title=title).first():
                continue
            start_utc = today + timedelta(days=days, hours=hour) - IST_OFFSET
            event = Event(
                organizer_id=users["organizer"].id,
                venue=Venue(name=venue_name, city=city, country_code="IN"),
                title=title, category=category,
                start_utc=start_utc, end_utc=start_utc + timedelta(hours=6),
                timezone="Asia/Kolkata", price_amount=price, currency="INR",
                is_free=(price == 0), status="approved",
            )
            db.session.add(event)
            print(f"created event: {title}")
        db.session.commit()
        print("Seed done.")


if __name__ == "__main__":
    run()