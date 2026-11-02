"""Local awareness web console. No messaging or credential collection."""
from __future__ import annotations

import secrets
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, session

from . import __version__, storage, tokens
from .settings import data_directory, secret_for


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    config = test_config or {}
    folder = Path(config.get("DATA_DIR") or data_directory())
    secret = config.get("SECRET_KEY") or secret_for(folder)
    app.config.update(
        SECRET_KEY=secret,
        DATA_DIR=folder,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=False,
        MAX_CONTENT_LENGTH=4096,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
        TESTING=config.get("TESTING", False),
    )
    db_path = folder / "lab.sqlite3"
    if not db_path.is_file():
        raise RuntimeError("Run 'python main.py init' before starting the server.")

    @app.before_request
    def only_loopback():
        if request.remote_addr not in ("127.0.0.1", "::1"):
            abort(403)

    @app.after_request
    def secure_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; font-src 'self'; object-src 'none'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html", version=__version__,
                               summary=storage.overview(db_path),
                               campaigns=storage.campaigns(db_path),
                               events=storage.activity(db_path, limit=12))

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=__version__, mode="local-demo")

    @app.get("/api/v1/summary")
    def summary():
        return jsonify(storage.overview(db_path))

    @app.get("/api/v1/campaigns")
    def get_campaigns():
        return jsonify(storage.campaigns(db_path))

    @app.get("/api/v1/events")
    def get_events():
        return jsonify(storage.activity(db_path))

    @app.get("/api/v1/report.csv")
    def report_csv():
        return Response(storage.export_csv(db_path), content_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="wps_demo_report.csv"'})

    def resolve(token: str) -> tuple[int, int]:
        values = tokens.verify(secret, token)
        if not values or not storage.eligible(db_path, *values):
            abort(404)
        return values

    @app.get("/practice/<token>")
    def practice(token: str):
        campaign_id, participant_id = resolve(token)
        nonce = secrets.token_urlsafe(32)
        session["training"] = {"token": token, "nonce": nonce}
        return render_template("practice.html", csrf=nonce)

    @app.post("/practice/<token>/acknowledge")
    def acknowledge(token: str):
        campaign_id, participant_id = resolve(token)
        pending = session.pop("training", None)
        supplied = request.form.get("csrf", "")
        if (not isinstance(pending, dict)
                or not isinstance(supplied, str)
                or not secrets.compare_digest(pending.get("token", ""), token)
                or not secrets.compare_digest(pending.get("nonce", ""), supplied)):
            abort(403)
        # Never read passwords, email fields, phone numbers, headers, or IP addresses.
        if not storage.acknowledge(db_path, campaign_id, participant_id):
            abort(403)
        return render_template("done.html")

    @app.route("/login", methods=["GET", "POST"])
    def deprecated_login():
        return "Credential collection is not supported", 410

    return app
