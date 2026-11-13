# Accounts and saved history (Phase 6)

**Off in production.** `ENABLE_ACCOUNTS=false` stays in `deploy/.env` on the server until
the owner records the institutional sign-off in `docs/DECISIONS.md` (spec Section 8):
stored inputs are patient-level clinical data linked to a clinician account. Nothing in
this file has been done on the server.

## What exists

- The calculator works without an account. With the feature on, a signed-in user can
  save a calculation (optionally under a case code), see their own saved calculations
  grouped by case code, open one as a report, delete it, and export all as CSV.
- Invite-only: no sign-up page and no e-mail. Accounts are created from the command
  line (below). Roles `user` and `admin`; `admin` is a label for whoever manages
  accounts and gives **no** access to other users' calculations.
- Stored per calculation: id, user, time, optional case code, the 11 inputs, the outputs
  computed by the server, the model version. No name, no identifier, no notes.
- Case code: 1–32 characters, Latin letters, digits, hyphen, underscore; must start with
  a letter or digit; no spaces. Enforced in the form, the API and the database.

## Security properties (each has a test)

- Passwords: argon2id; minimum 12 characters; never logged; never a command-line argument.
- Session: random token in a cookie (`__Host-` prefix, `HttpOnly`, `Secure`,
  `SameSite=Lax`); only its SHA-256 is stored. 30 minutes idle, 12 hours at most
  (`SESSION_IDLE_MINUTES`, `SESSION_MAX_HOURS`). Changing a password ends the user's
  other sessions; deactivating a user ends all of them.
- CSRF: every state-changing request needs the session's token in `X-CSRF-Token`, and a
  cross-site `Origin` is refused, login included.
- Login: one answer for wrong password, unknown address and inactive account; 10
  attempts per 15 minutes per client address and e-mail.
- Isolation: every query for calculations is filtered by the signed-in user. Someone
  else's id and a non-existent id give the same 404.
- Logs: method, path, status, codes. No e-mail, password, token, case code or input.
- With the flag off, the endpoints do not exist and no database code is loaded.

## Enabling (owner, on the server, only after the sign-off)

1. In `deploy/.env`: `ENABLE_ACCOUNTS=true` and a `POSTGRES_PASSWORD`
   (`openssl rand -hex 24`). The file is not in git.
2. `sudo deploy/deploy.sh` — starts PostgreSQL, runs the migration, restarts the API.
   Check memory first (`free -h`): the database container may use up to 512 MB.
3. Create accounts (the password is typed at a prompt):

       cd ~/neomortalsurv/deploy
       sudo docker compose --env-file .env -f docker-compose.yml -f docker-compose.accounts.yml \
         exec api python -m app.cli create-user someone@example.org

   Other commands: `reset-password EMAIL`, `deactivate EMAIL`, `activate EMAIL`,
   `list-users`, `purge-sessions`. Add `--admin` to `create-user` for an admin.
4. Nightly backup: add the cron line from the top of `deploy/backup.sh`.

To switch the feature off again: `ENABLE_ACCOUNTS=false`, `deploy/deploy.sh`. The data
stays in the `pg_data` volume until that volume is removed.

## Backup and restore

- `deploy/backup.sh` writes `pg_dump` custom-format files to `/var/backups/neomortalsurv`
  (root-only), checks each can be listed by `pg_restore`, and deletes files older than
  14 days.
- `deploy/backup.sh --restore FILE` replaces the database contents with a dump.
- **Rehearsed once, locally, on 2026-11-13, with synthetic data:** one user and three
  calculations saved; backup taken; database volume destroyed and recreated empty;
  restore run; afterwards 1 user, 3 calculations, schema revision `0001`, the user can
  sign in, and the CSV export is byte-identical to the one taken before the backup.
- Not rehearsed: on the server (the feature is off there). `TODO(owner)`: a copy of the
  dumps off the server, encrypted, and who may hold it.

## Open, for the owner

- Institutional / ethics sign-off and the applicable personal-data rules, including
  where the server must be located (spec Section 8). **Blocks enabling.**
- Invite-only confirmed? (spec default, in force)
- Retention: how long saved calculations are kept, and what happens to them when a
  clinician leaves. Today: kept until the user deletes them or the account is deleted.
- All new interface wording is `TODO(clinical-review)`.
