# Technical architecture

WPS 2.0 is a private legacy educational prototype, organized around a
Tkinter desktop interface, MySQL records, local awareness website and
original browser automation code.

## Components

| Component | Role |
| --- | --- |
| `main.py` | Start a loopback web service and the Tkinter GUI |
| `gui.py` | Participant and campaign management screens |
| `sender.py` | Original browser messaging integration for authorized lab use |
| `db_utils.py` | Local database access and event tracking |
| `encrypt_utils.py` | Authentic, time-limited participant link tokens |
| `phishing_server/app.py` | Minimal Flask awareness website |
| `report_exporter.py` | Aggregated reports with restricted data exposure |
| `tests/` | Isolated regression checks |

## Awareness flow

1. The link contains an authenticated Fernet token with user and campaign IDs.
2. The Flask route checks the token and its age, then records a click event.
3. The user sees a security awareness explanation directly.
4. No credential form, email capture or login verification code is required.
5. A legacy POST to `/login` returns HTTP 410 without inspecting form fields.

The application does not implement or claim a verified remote deployment. The
web service is bound to 127.0.0.1 to minimize exposure, so links cannot
reach it directly from another machine without a separately authorized,
reviewed deployment design.

## Known work remaining

* GUI and sender flows need manual Windows, Chrome and database integration testing.
* Historical database rows may still contain sensitive data from older versions.
* A large tracked ChromeDriver binary should be reviewed for safe removal.
* The original schema lacks strong uniqueness constraints and migration support.
* The project is an educational prototype rather than production software.
