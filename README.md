# event-aggregator

Event discovery platform for students and communities worldwide: college fests, hackathons, workshops and meetups in one feed, with QR check-in and verified sponsor reports.

Global-ready, launching in Bengaluru, expanding city by city.

## The problem

College fests and small community events run on WhatsApp forwards and Instagram posts.

- **Students** miss events they'd attend, because listings are scattered across dozens of pages and groups.
- **Organizers** can't reach beyond their own followers, and big ticketing platforms charge high commissions.
- **Sponsors** pay for fests with no verified proof of how many students they reached.

## The solution

1. **City event feed** — every student event in one place, filtered by date, type, free/paid and distance.
2. **Poster-to-listing** — organizers upload a poster or paste a WhatsApp forward; the listing fills itself in.
3. **Free registration + QR check-in** — real attendance numbers for every event.
4. **Sponsor reports** — verified registrations, check-ins and audience breakdown.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + Tailwind CSS (PWA) |
| Backend | Flask REST API |
| Database | PostgreSQL (Supabase); SQLite for local development |
| Auth | JWT (flask-jwt-extended), hashed passwords |
| Hosting | Vercel (frontend), Render (backend), Supabase (database) |

### Global-ready rules

- All times stored in **UTC**; each event keeps its IANA timezone (`Asia/Kolkata`, `Asia/Tokyo`).
- Prices = amount + **ISO 4217** currency (`INR`, `USD`, `JPY`).
- Locations = **ISO 3166** country code + city + latitude/longitude.
- All UI text goes in translation files (no hard-coded strings).

## Project structure

```
event-aggregator/
├── backend/          Flask API
│   ├── app/
│   │   ├── __init__.py    app factory
│   │   ├── extensions.py  db, jwt, cors, migrate
│   │   ├── models.py      User, Venue, Event, Registration
│   │   └── auth.py        /api/auth/register, /login, /me
│   ├── tests/
│   ├── config.py
│   ├── run.py
│   └── requirements.txt
└── frontend/         Next.js app (to be created)
```

## Run the backend locally

```
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env      # Windows  (macOS/Linux: cp .env.example .env)
python run.py
```

The API runs at http://localhost:5000. Check http://localhost:5000/api/health.

Run tests with `python -m pytest`.

### API so far

| Method | Endpoint | Body | Notes |
|---|---|---|---|
| GET | `/api/health` | — | Health check |
| POST | `/api/auth/register` | `name, email, password, role?, country_code?, city?, timezone?` | role: `student` or `organizer` |
| POST | `/api/auth/login` | `email, password` | Returns `access_token` |
| GET | `/api/auth/me` | — | Header `Authorization: Bearer <token>` |

## Design theme — "Midnight"

- Ink `#1F1F2E`, black `#12121A`, paper `#FAF8F3`, muted `#55525C`, border `#E7E3D8`
- Accent orange `#FF5A1F` only for primary buttons, "Free" badges, active filters and success states
- Fonts: Space Grotesk (headings), Inter (body)
- Poster-first cards; the interface stays calm so event posters stand out

## Team workflow

- Never push directly to `main`.
- One branch per feature: `feature/event-feed`, `feature/qr-checkin`.
- Open a pull request, get one teammate's review, then merge.

## Roadmap

- [x] Backend setup, models, signup/login
- [ ] Event submission, admin approval, event feed with filters
- [ ] Poster-to-listing
- [ ] Registration + QR check-in
- [ ] Sponsor reports
- [ ] Frontend + deployment