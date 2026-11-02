# Authorized real-recipient awareness campaigns

WPS2.0 retains its **original authorized WhatsApp campaign delivery** and its data-backed participant and campaign management. The application exists to support legitimate security awareness operations and controlled red-team/social-engineering exercises performed under documented organizational approval.

This branch adds a strict scope gate to avoid accidental deliveries. It does not turn the project into a fictional-only simulator.

## Approval model

A real campaign requires all of the following:

* A recorded authorization reference and approving owner.
* An explicit campaign ID and valid UTC time window.
* An exact list of approved recipient IDs **and** approved phone numbers.
* A maximum recipient count for that approval.
* An explicitly selected set of active recipients from the existing GUI filters.
* A final human review and confirmation in the desktop application.

The scope file is **private, local and never committed**. The values below are fictional examples from the reserved 202-555 range.

Copy `approval.example.json` to `.local/campaign-approval.json`, update it to match your organization's approved exercise, and keep it outside Git.

```powershell
$env:WPS_CAMPAIGN_APPROVAL_FILE = (Resolve-Path .local/campaign-approval.json).Path
```

Run the existing application normally. In the Campaigns tab, select a campaign, apply the authorized participant filters and review the confirmation. The same approval check runs again in the sending worker immediately before any browser session starts. The application refuses sending when there is no approval, the approval has expired, campaign IDs mismatch, selected IDs exceed the scope, or a contact phone differs from the approved list.

`run_whatsapp_campaign(...)` is **dry run by default**. The GUI provides the explicit real delivery invocation only after scope validation and operator confirmation.

## Data flow

```text
Approved campaign + local recipient register + change ticket
                          |
                   Preflight validation
                    |            |
                    | invalid    | valid
                    v            v
               DENY SEND     Preview scope
                                  |
                         Operator confirmation
                                  |
                          Revalidate approval
                                  |
                         Authorized WhatsApp
                         awareness messaging
                                  |
                         Local minimal audit
```

Existing individual tracking links, campaign events and private MySQL storage remain in place. No public webhook or participant lookup API is added. The awareness landing page does not accept or record credentials.

## Operator responsibilities

A local approval file records the requested scope. **It does not cryptographically prove that an organization granted permission.** Operators must verify the authorization and applicable communications/consent policy independently before entering it. Preserve the approved message text and exercise boundaries within the organization's own change process. Review applicable messaging-platform rules.

Recipients may be real because this is a real awareness system. Consequently, names, phone numbers, email addresses and participation events are operational personal data. Keep those values in authorized local storage only, enforce retention rules and never add them to Git, screenshots or demo exports.

This branch reduces accidental mistakes. It does not implement multiuser RBAC, enterprise SSO, retention automation, encrypted personal-data storage or independent audit signing. Those remain production security requirements.

## Audit events

The additional `.local/campaign-audit.jsonl` records approval reference, campaign ID, event kind, UTC time and recipient counts. It never writes phone numbers, message bodies, emails or credentials.

The existing detailed application logs should also be reviewed for accidental contact identifiers. The sender now avoids logging full phone numbers when attempting and dispatching messages.

## Test without messaging

Tests validate the approval gate entirely offline and cannot send messages or open Chrome.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_campaign_approval.py
```

Review end-to-end Chrome, MySQL, GUI, campaign-link and recipient selection behavior only in an approved lab environment. Never run real sends against unapproved accounts.

## Consolidation with WPS V1

WPS V1 introduced a more modular organization of GUI tabs, configuration, services and CSV/Excel output safeguards. WPS2.0 retained richer campaign/participant workflows and reporting. Consolidation should preserve both the legitimate real delivery path and the latest privacy safeguards.

The current PR is **the first incremental security step**, not a completed migration or a claim that all V1 features have been ported. Recommended integration order:

1. Preserve WPS2.0 recipient and sender functionality.
2. Retain V2's credential-free awareness page and safe report export.
3. Introduce approved-scope preflight, audit and dry-run, as implemented here.
4. Gradually extract the monolithic GUI into modules based on V1.
5. Reconcile database schemas, report compatibility and current V1 security tests.
6. Test end-to-end with only institutional test recipients before a controlled rollout.
7. Move V1 into an archive only after the combined application is verified.
