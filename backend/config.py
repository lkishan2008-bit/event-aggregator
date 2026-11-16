import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_url():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        # Local development fallback: a SQLite file next to this config.
        return "sqlite:///" + os.path.join(BASE_DIR, "dev.db")
    # Some providers give "postgres://", SQLAlchemy needs "postgresql://".
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me-in-env-file-32b")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    # Amazon SES (leave SES_SENDER empty to print emails in the terminal instead)
    SES_SENDER = os.getenv("SES_SENDER", "").strip()
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

    # Razorpay (paid tickets). Leave both empty to use a fake "test payment" screen for demos.
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()

    # Secret for the hourly "sync event feeds" call from a cron service (leave empty to disable that URL)
    CRON_SECRET = os.getenv("CRON_SECRET", "").strip()
    # Re-import calendar feeds in the background while the server runs (minutes; 0 = off)
    FEED_SYNC_MINUTES = int(os.getenv("FEED_SYNC_MINUTES", "60"))

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]


class TestConfig(Config):
    """Tests never use real keys or services, whatever is in .env."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    FEED_SYNC_MINUTES = 0
    SES_SENDER = ""
    RAZORPAY_KEY_ID = ""
    RAZORPAY_KEY_SECRET = ""
    CRON_SECRET = ""