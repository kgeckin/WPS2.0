# Unified architecture

WPS Awareness Lab consolidates two historically separate educational prototypes into one carefully scoped local environment.

```text
                One trusted local computer
   ┌─────────────────────────────────────────────────┐
   │  CLI        Tkinter read-only      Web dashboard │
   │   │                │                     │       │
   │   └────────────────┴─────────────────────┘       │
   │                    │                            │
   │         Local Python services                  │
   │     SQLite ── token signing ── reports          │
   │                    │                            │
   │            Flask (127.0.0.1)                    │
   │                    │                            │
   │     Transparent education and acknowledgement   │
   └─────────────────────────────────────────────────┘
        No remote send / No credential collection
```

## Ownership of the combined features

| Concept | Previously in WPS | Previously in WPS2.0 | Unified approach |
| --- | --- | --- | --- |
| Campaign and participant management | Modular Tkinter views | Large monolithic GUI | SQLite-backed read-only Tkinter overview and web console |
| Awareness page | Local form with session-bound nonce | Immediate awareness content | Explicit educational page with single-use acknowledgement and CSRF |
| Link authenticity | Fernet token module | Fernet utility module | Short-lived signed token with no personal data |
| Reporting | DataFrame export sanitizer | Summary Excel exporter | Restricted CSV of pseudonymous acknowledgements |
| Storage | MySQL services | MySQL utilities | SQLite for isolated local demonstration |
| Browser automation | Selenium/WhatsApp integration | Selenium/WhatsApp sender | Retired from maintained app; no outbound delivery |
| Packaging | Many direct modules | Several monolithic files | One `wps_lab` package and shared local data |
| QA | Route and privacy tests | Awareness and report tests | Consolidated deterministic unit and integration tests |

**Feature equivalence is intentionally not one-to-one.** The current app prioritizes a verifiable, minimal, transparent local demonstration. It does not retain automatic message delivery, remote training campaigns, complete legacy GUI editing or MySQL reporting. Those operations cannot be asserted compatible without authorized migration and end-to-end testing.

## Data model

* `campaigns`: ID, illustrative scenario name, lifecycle state, creation time.
* `participants`: synthetic ID, alias such as `TRAIN-001`, explicit demo consent flag.
* `events`: campaign ID, participant ID, `acknowledged` event and UTC timestamp.

A unique key prevents repeated acknowledgement events for the same alias and campaign. No email, phone number, password, authentication tokens or IP address columns are present.

## Practice flow

1. Local CLI generates a signed URL for an eligible synthetic alias and active campaign.
2. The local browser opens a clearly identified training page.
3. GET only renders educational content and prepares a CSRF nonce in a secure session.
4. POST requires the original token and matching one-time nonce.
5. The app records a minimal acknowledgement and returns a completion page.

Only `127.0.0.1` and `::1` clients are permitted. No proxy or external network listening is supported.

## Intended future work

Potential future enhancements include stronger local admin login, accessible campaign editing with explicit consent records, optional Windows packaging and a reviewed database migration tool. They are not implemented in this branch. No live corporate identity provider, campaign dispatch or real-target phishing simulation is planned.
