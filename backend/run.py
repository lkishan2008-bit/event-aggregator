import os

from app import create_app
from app.extensions import db
from app.feeds import start_background_sync

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # quick start; switch to `flask db migrate/upgrade` once the schema settles
    # debug mode runs the app in a child process; start the hourly feed import only there (once)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_background_sync(app)
    app.run(debug=True, port=5000)