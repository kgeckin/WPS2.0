> **Authorized awareness project scope:** WPS2.0 was developed to conduct approved organizational security awareness campaigns with **real, in-scope recipients**. The original WhatsApp Web sender, participant/campaign manager and training outcome reporting remain part of the codebase. The in-progress consolidation adds recipient authorization preflight, an operator confirmation and private auditing without reducing the product to a fictional-only application. [Authorized campaign controls](docs/AUTHORIZED_CAMPAIGNS.md). This work is under review and is not yet a verified production deployment.

<div align="center">

<img src="docs/assets/cover.svg" width="100%" alt="WPS 2.0, controlled security awareness lab" />

**A corporate security awareness simulator designed for documented, authorized real-recipient exercises.**

[Getting started](#getting-started) · [Architecture](docs/ARCHITECTURE.md) · [Security](docs/SECURITY.md)

</div>

## Overview

WPS 2.0 brings together a Tkinter interface, an educational campaign database,
a local training awareness website and the original browser integration code.
This repository is a historical security internship project that is being
refactored for clarity and safer demonstrations.

The local awareness page shows educational content directly. It does not
request or store passwords, verification codes or submitted email addresses.

## What it includes

* Campaign and participant management in a desktop interface.
* Authenticated, time-limited training links.
* A local Flask awareness website with no credential entry form.
* Local MySQL event records and privacy-restricted Excel reports.
* Documentation and regression checks for the key security boundaries.

## Getting started

**Prerequisites:** Python 3.11, a local MySQL development instance and,
for the original desktop/browser features, Windows and Google Chrome.

```powershell
git clone https://github.com/kgeckin/WPS2.0.git
cd WPS2.0
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python generate_key.py
```

Configure the local database values in `.env` and initialize the schema
from [wps_local.sql](wps_local.sql) in an isolated test database.

```powershell
python main.py
```

The training web service is bound to `127.0.0.1:5000` by default.
It is not a public or remotely reachable service. The original browser
messaging functionality requires separately approved test accounts,
test recipients and integration verification.

## Repository structure

```text
WPS2.0/
├── docs/                 # Architecture, security notes, cover
├── phishing_server/      # Local credential-free awareness service
├── tests/                # Isolated privacy and route tests
├── gui.py                # Desktop UI
├── db_utils.py           # MySQL access and event tracking
├── encrypt_utils.py      # Time-limited encrypted links
├── sender.py             # Legacy browser integration
├── report_exporter.py    # Minimal-data Excel reports
├── main.py               # Local application entrypoint
├── .env.example          # Example, no real credentials
└── requirements.txt
```

## Validation

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
```

The new tests use mock event loggers and database connections. A complete
Windows, Chrome and MySQL integration test has not yet been confirmed.

## Architecture & decisions

See [Architecture](docs/ARCHITECTURE.md) for the training flow, service
boundaries and known integration gaps.

## Security & limitations

* Authorized training with informed participants only.
* No credential capture UI, and no credential collection in the retained API.
* Links expire and the local web server does not listen on external interfaces.
* Report export excludes passwords, submitted addresses and diagnostic logs.
* Historical database rows from older versions are **not** automatically deleted.
* Third-party content and the tracked browser driver require a rights and
  binary hygiene review before redistribution.

Read [Security & privacy](docs/SECURITY.md) before any demonstration.
This is an educational prototype, not a verified production deployment.

## License

No license file is currently present. Do not assume redistribution rights
for this code, embedded assets or third-party materials.
