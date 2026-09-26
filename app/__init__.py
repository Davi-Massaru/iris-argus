"""Agentic IRIS administration control plane."""

from __future__ import annotations

from flask import Flask

from app.api.routes import api
from app.mvp.routes import bp
from app.repositories.iris_repository import IRISRepository


def create_app(repository=None, *, testing: bool = False) -> Flask:
    app = Flask(
        __name__, static_folder="../frontend/static", template_folder="../frontend/templates"
    )
    app.config.update(TESTING=testing, MAX_CONTENT_LENGTH=1_048_576)
    if testing:
        app.config["AGENTIC_CSRF_SECRET"] = b"test-only-csrf-secret"
    app.extensions["agentic_repository"] = repository or IRISRepository()
    app.register_blueprint(api)
    app.register_blueprint(bp)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    return app
