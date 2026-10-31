"""Start a local training awareness web server and the desktop GUI."""

from __future__ import annotations

import os
import threading

from phishing_server.app import app


def start_flask() -> None:
    # Local-only by default. External exposure needs a separate security review.
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=False,
        use_reloader=False,
    )


def start_gui() -> None:
    from gui import WPSGUI

    WPSGUI().mainloop()


if __name__ == "__main__":
    thread = threading.Thread(target=start_flask, daemon=True)
    thread.start()
    start_gui()
