"""Fill the local database with demo accounts and events.

Run from the backend folder:   python seed.py
Safe to run again: it skips anything that already exists.
All events here are SAMPLE data for development and demos.
"""
from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import Event, User, Venue
from app.utils import utcnow_naive

ACCOUNTS = [
    ("Admin", "admin@example.com", "Admin@12345", "admin"),
    ("Demo Student", "student@example.com", "Student@123", "student"),
]

# Demo organizers (all use password Organizer@123)
ORGANIZERS = {
    "rvce": "RVCE Tech Club",
    "iisc": "IISc Bio Society",
    "pes": "PES Design Collective",
    "bmsce": "BMSCE Coding Club",
    "christ": "Christ University Cultural Committee",
    "iiitb": "IIIT-B Robotics Club",
    "msrit": "MSRIT Entrepreneurship Cell",
    "dsce": "DSCE Music Club",
    "community": "BangPypers Community",
}

# (title, category, days from now, local hour, duration hrs, price, organizer key, venue, address, description)
EVENTS = [
    ("HackRV 3.0", "hackathon", 6, 9, 24, 0, "rvce", "RVCE Main Auditorium", "Mysore Road, RV Vidyaniketan",
     "A 24-hour student hackathon. Build in teams of 2-4 on themes like health, climate and fintech. Food and mentoring included."),
    ("Intro to CRISPR Workshop", "workshop", 5, 14, 3, 0, "iisc", "IISc Biological Sciences Building", "CV Raman Road, Malleshwaram",
     "Hands-on introduction to CRISPR gene editing: how it works, lab safety, and a guided demo. Open to all biotech students."),
    ("Figma to Prototype Design Sprint", "workshop", 8, 10, 6, 299, "pes", "PES University, Design Lab", "100 Feet Ring Road, Banashankari",
     "A one-day design sprint: research, wireframes and a clickable prototype in Figma. Bring a laptop."),
    ("CodeStorm Competitive Programming", "hackathon", 9, 10, 5, 0, "bmsce", "BMS College of Engineering, CSE Block", "Bull Temple Road, Basavanagudi",
     "Solo competitive programming contest with prizes for the top 3. Problems from easy to hard; any language allowed."),
    ("Christ Cultural Fest Day 1", "fest", 12, 11, 9, 199, "christ", "Christ University Main Campus", "Hosur Road",
     "Dance, music, theatre and food stalls. Inter-college competitions all day, band night in the evening."),
    ("Build a Line-Follower Robot", "workshop", 13, 14, 4, 149, "iiitb", "IIIT Bangalore", "26/C Electronics City",
     "Beginner robotics workshop. Assemble and program a line-following robot with Arduino. Kits provided."),
    ("Startup Pitch Night", "meetup", 7, 17, 3, 0, "msrit", "MSRIT Seminar Hall", "MSR Nagar, Mathikere",
     "Student founders pitch to investors and mentors. Networking afterwards. Great for anyone curious about startups."),
    ("Unplugged Acoustic Evening", "fest", 15, 18, 3, 99, "dsce", "Dayananda Sagar College Open Air Theatre", "Shavige Malleshwara Hills, Kumaraswamy Layout",
     "Live acoustic performances by student bands from colleges across Bengaluru. Open mic slots available."),
    ("BangPypers Monthly Meetup", "meetup", 7, 11, 3, 0, "community", "Koramangala Community Space", "80 Feet Road, Koramangala",
     "Monthly Python meetup with two talks and lightning talks. All levels welcome."),
    ("8th Mile Cultural Fest", "fest", 19, 12, 10, 199, "rvce", "RVCE Main Grounds", "Mysore Road, RV Vidyaniketan",
     "RVCE's annual cultural fest: pro-shows, competitions and food. Open to students from all colleges."),
]

IST_OFFSET = timedelta(hours=5, minutes=30)


def get_or_create_user(name, email, password, role):
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email, role=role, country_code="IN",
                    city="Bengaluru", timezone="Asia/Kolkata", email_verified=True)
        user.set_password(password)
        db.session.add(user)
        print(f"created {role}: {email} / {password}")
    return user


def run():
    app = create_app()
    with app.app_context():
        db.create_all()

        for name, email, password, role in ACCOUNTS:
            get_or_create_user(name, email, password, role)
        organizers = {
            key: get_or_create_user(name, f"{key}@example.com", "Organizer@123", "organizer")
            for key, name in ORGANIZERS.items()
        }
        db.session.commit()

        today = utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)
        for title, category, days, hour, hours, price, org, venue_name, address, description in EVENTS:
            if Event.query.filter_by(title=title).first():
                continue
            start_utc = today + timedelta(days=days, hours=hour) - IST_OFFSET
            db.session.add(Event(
                organizer_id=organizers[org].id,
                venue=Venue(name=venue_name, address=address, city="Bengaluru", country_code="IN"),
                title=title, category=category, description=description,
                start_utc=start_utc, end_utc=start_utc + timedelta(hours=hours),
                timezone="Asia/Kolkata", price_amount=price, currency="INR",
                is_free=(price == 0), status="approved",
            ))
            print(f"created event: {title}")
        db.session.commit()
        print("Seed done.")


if __name__ == "__main__":
    run()