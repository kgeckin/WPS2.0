"""
main.py
-------
Entry point for WPS application.
Starts both Flask awareness server and GUI in parallel.
"""

import threading
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "phishing_server"))
from app import app


def start_flask():
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "phishing_server"))
    from app import app
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def start_gui():
    from gui import WPSGUI
    app = WPSGUI()
    app.mainloop()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    start_gui()
