"""Local, credential-free training awareness web application.

The original repository referenced this missing package. The replacement
intentionally serves training content without a credential capture flow.
"""

from __future__ import annotations

from collections.abc import Callable

from flask import Flask, abort, render_template, request

TokenDecoder = Callable[[str], tuple[int | None, int | None]]
EventLogger = Callable[..., bool]


def create_app(
    token_decoder: TokenDecoder | None = None,
    event_logger: EventLogger | None = None,
) -> Flask:
    if token_decoder is None:
        from encrypt_utils import decrypt_token
        token_decoder = decrypt_token

    if event_logger is None:
        from db_utils import log_campaign_tracking
        event_logger = log_campaign_tracking

    app = Flask(__name__, template_folder="templates")

    @app.after_request
    def prevent_caching(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    def health():
        return "ok", 200

    @app.get("/redirect")
    @app.get("/r/<token>")
    def training_link(token: str | None = None):
        value = token or request.args.get("data", "")
        if not value or len(value) > 4096:
            abort(400, description="invalid training link")
        user_id, campaign_id = token_decoder(value)
        if (
            not isinstance(user_id, int)
            or not isinstance(campaign_id, int)
            or user_id <= 0
            or campaign_id <= 0
        ):
            abort(400, description="invalid or expired training link")

        if not event_logger(
            user_id, campaign_id, clicked=True, opened=True, compromised=False
        ):
            abort(503, description="training event could not be recorded")

        return render_template("awareness.html"), 200

    @app.post("/login")
    def retired_login():
        # Do not process or read credentials, even on a crafted legacy request.
        return "credential collection is disabled", 410

    return app


app = create_app()
