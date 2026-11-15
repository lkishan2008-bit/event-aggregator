from app import create_app
from app.extensions import db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # quick start; switch to `flask db migrate/upgrade` once the schema settles
    app.run(debug=True, port=5000)