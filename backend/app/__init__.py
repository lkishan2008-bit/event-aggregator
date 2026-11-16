from flask import Flask, jsonify

from config import Config

from .extensions import cors, db, jwt, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401  (registers models with SQLAlchemy)
    from .auth import bp as auth_bp
    from .events import bp as events_bp
    from .registrations import bp as registrations_bp
    from .checkin import bp as checkin_bp
    from .poster import bp as poster_bp
    from .feeds import bp as feeds_bp
    from .trust import bp as trust_bp
    from .report import bp as report_bp
    from .saved import bp as saved_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(poster_bp)
    app.register_blueprint(feeds_bp)
    app.register_blueprint(trust_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(saved_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app