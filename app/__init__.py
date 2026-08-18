from __future__ import annotations
from typing import Optional
from flask import Flask

from app.routes import api


def create_app(config: Optional[dict] = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)

    app.register_blueprint(api)
    return app
