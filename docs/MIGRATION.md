# WPS / WPS2.0 consolidation

## Decision

**Canonical development target: `kgeckin/WPS2.0`.** The older `kgeckin/WPS` repository remains a historical reference. Neither repository should be deleted before the owner approves archival and preservation. GitHub repository renaming, deletion and archive actions are separate from this code Pull Request.

## Comparative inventory

| Legacy element | Source | Outcome |
| --- | --- | --- |
| Tkinter campaign and participant views | WPS `gui/tabs/`, WPS2 `gui.py` | Replaced by a safe Tkinter manager of synthetic campaigns and consent, plus read-only web dashboard |
| Campaign metadata | WPS `services/db_service.py`, WPS2 `db_utils.py` | Recreated in a minimal synthetic SQLite schema |
| Encrypted tracking links | WPS `services/crypto_service.py`, WPS2 `encrypt_utils.py` | Replaced by signed 15-minute local practice URLs |
| Session-bound educational acknowledgement | WPS `services/flask_service.py` | Preserved as one-time CSRF/session bound acknowledgement |
| Direct awareness explanation | WPS2 `phishing_server/app.py` | Retained in a transparent educational page |
| Export formula sanitization | WPS `services/import_export_service.py`, WPS2 `report_exporter.py` | Preserved for minimal pseudonymous CSV reporting |
| WhatsApp automation | WPS `services/whatsapp_service.py`, WPS2 `sender.py` | Excluded from maintained app |
| ChromeDriver binaries | Both repositories | Removed from new active tree only |
| Legacy MySQL and design files | Both repositories | Retained in historical revisions, not migrated or imported |

## Data handling

No actual participant lists, historical click events, passwords, phone numbers, training submissions, MySQL databases or browser profiles are migrated. Synthetic `TRAIN-001` style aliases are created on initialization. The original SQL databases must remain subject to their existing owner's separate retention policy.

## Deployment gate

Before merging into `main`, confirm:

1. A fresh virtual environment can install dependencies.
2. The test suite passes without a running MySQL server, Chrome or a messaging account.
3. Local dashboard and practice flow work in a browser.
4. A forged/expired URL and invalid CSRF request are rejected.
5. The CSV contains only synthetic aliases and event timestamps.
6. The local secret and SQLite database are ignored by Git.
7. Outbound messaging automation and the ChromeDriver binary are absent from the release tree.
8. Desktop Tkinter view opens in a supported graphical environment.
9. Existing historical repositories and third-party content are handled deliberately.

## Old repository disposition

After an approved merge and review, update `kgeckin/WPS` README to point to WPS2.0, then consider marking it archived in GitHub settings. Do not erase its history or change visibility without first reviewing historic data exposure and permissions. The old repository may contain independent source lineage useful for attribution.
