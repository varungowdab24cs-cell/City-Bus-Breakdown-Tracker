from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    if isinstance(config_class, dict):
        app.config.from_mapping(config_class)
    else:
        app.config.from_object(config_class)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}})

    from . import models  # noqa: F401
    from .routes import api

    app.register_blueprint(api, url_prefix="/api")

    with app.app_context():
        from .seed import seed_database

        seed_database()

    return app
