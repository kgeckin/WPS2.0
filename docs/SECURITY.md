# Security and privacy review

## Maintained demonstration boundary

The consolidated WPS app is **local only** and has no real messaging sender. It never requests or stores usernames, passwords, verification codes, email addresses, phone numbers, browser identifiers or client IP addresses as training data. It uses entirely fictional participant codes in a seeded SQLite database.

### Local-only enforcement

* The Flask server binds to `127.0.0.1`.
* Requests originating from non-loopback remote addresses are rejected.
* Untrusted Host headers are rejected.
* `robots` indexing is discouraged via `X-Robots-Tag`.
* A 4 KiB per-request size bound is enforced.
* Responses use no-store caching, no framing and a restrictive Content Security Policy.
* There are no externally loaded JavaScript libraries or analytics.

### Authentication and integrity

The private signing key is randomly generated on `python main.py init` and written under the ignored `var/` directory. It is not displayed in the console and must not be uploaded. An environment override is supported but must itself be securely generated and at least 40 characters long.

Practice links are signed and expire after 15 minutes. Only explicitly consented demo aliases in active campaigns may use them. Campaign creation, lifecycle changes and consent management are available only through the local CLI and Tkinter process. The unauthenticated web API exposes no campaign-changing endpoint. Revoking demo consent deletes related acknowledgement records. A browser acknowledgement uses a session-bound one-time CSRF token. Repeated or forged requests are denied. The GET operation never records a completed exercise.

The dashboard has **no user login** because it is only a single-user local learning lab. That is a production blocker, not a recommendation to expose it to an untrusted network.

### Minimal reports

CSV exports contain only the campaign label, synthetic alias, acknowledgement type and time. Cells resembling spreadsheet formulas are prefixed with an apostrophe. The exporter does not read legacy password, submitted email, browser metadata or IP columns because they do not exist in the new schema.

### Legacy repo concerns

Historical WPS versions contained MySQL schema columns for credential fields and Selenium messaging code. Replacing code does **not delete** prior database content, archived logs or Git commits. The new version does not import these databases. The original ChromeDriver binary may remain accessible in older commit history even after it is removed from the active tree.

Before making any production deployment or migrating a real exercise:

1. Obtain written authorization and data ownership approval.
2. Inspect legacy database files, exports and backups for personal data.
3. Sanitize data separately and validate retention obligations.
4. Assess dependency provenance, binary provenance and third-party asset rights.
5. Design authentication, TLS, RBAC, auditable consent and rate limiting.
6. Complete security tests, independent code review and authorized penetration testing.

## Intentional exclusions

* Automated WhatsApp or email delivery and contact importing.
* Credential capture, impersonated login forms and password reporting.
* Remote network scans, agent deployment, process execution and recipient discovery.
* Access to organization or customer accounts without approval.

The project is a transparent educational lab, not an end-to-end phishing operations product.
