# Security and privacy

## Scope

This repository is private. Use it only for exercises approved by the
responsible organization, with informed participants and authorized test data.
Never use it for real credential harvesting or unapproved outreach.

## Credential handling

This version supplies no credential entry page. The former login event API
accepts legacy positional arguments only for compatibility and discards them.
Database queries and reports retrieve identifiers and timestamps rather
than passwords, email submissions, browser identifiers or IP addresses.

Report export never enables password output, even if the legacy
`include_passwords=True` flag is passed. Contact fields and diagnostic
logs are excluded from the generated workbook by default.

## Older database records

Code updates do not delete information already saved by previous releases.
An authorized data owner must review data retention and backups before
removing any old values.

The following is an illustrative cleanup statement and must not be run on
an existing database without an explicit retention and backup review:

```sql
UPDATE login_attempts
SET submitted_email = NULL,
    submitted_pass = NULL,
    user_agent = NULL,
    ip_address = NULL;
```

The old schema permits these fields to be nullable. Keep audit records only
for the period and purpose authorized by the responsible data owner.

## Boundaries

* Flask listens on 127.0.0.1, not a public interface.
* Training tokens expire based on `TOKEN_VALID_SEC`.
* API keys, MySQL passwords and the Fernet key belong in an ignored .env file.
* Never commit real participant lists, browser profiles, exports or customer data.
* Review licensing and redistribution rights for all supplied training assets.
* No production security assessment or full end to end validation has been completed.
