# ReelTalk — Phase 1 Execution Plan (Handoff Document)

**Status:** Planning complete, ready for execution. This document is self-contained: a fresh session with no prior context should be able to execute Phases 0–4 from it alone.

**Written:** 2026-08-21, end of planning session 2 (supersedes HANDOFF.md for execution; HANDOFF.md remains as the session-1 decision record and is deleted when Phase 1 completes).

---

## 1. Project purpose

**ReelTalk** is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) retooled as a federated (ActivityPub) social site for **film reviews**. The owner is a B-movie/cult-film enthusiast; the name is final (a pun on "real talk").

- Fork repo: https://github.com/minnixtx/reeltalk (owner GitHub: `minnixtx`)
- Upstream codebase: BookWyrm at commit `afd5ec305` ("New Crowdin updates (#4053)")

**Phase 1 (this plan):** rebrand the fork to ReelTalk and get a running, Docker-deployed site with simplified self-hosting. **No film-domain changes.** The film domain model is Phase 2 and will be designed with the owner later — do not make Phase 2 design decisions in this execution.

## 2. License & attribution constraints (READ FIRST)

BookWyrm is licensed under the **Anti-Capitalist Software License v1.4** (© 2020 Mouse Reeve), **not** AGPL. Hard rules:

1. `LICENSE.md` must remain **byte-identical** to upstream. It is excluded from all renames/edits. Verify at the end with a diff against the original.
2. Attribution to Mouse Reeve / BookWyrm is **never stripped**. Adapted docs (README, CONTRIBUTING, CODE_OF_CONDUCT, FEDERATION) must keep provenance lines (e.g., "ReelTalk is a fork of BookWyrm" + upstream links).
3. If the project ever moves toward commercial use, **stop and flag the owner** — ACRL forbids it.

## 3. Environment facts

| Fact | Value |
|---|---|
| Machine | Fedora 44, KDE, HP Z2 G4, ~938 GB free disk |
| git | 2.55; `gh` CLI authenticated as `minnixtx` (repo scope — can push to minnixtx/reeltalk) |
| Docker | **Not installed.** Owner approved install via dnf (Fedora native packages, no third-party repo): `sudo dnf install moby-engine docker-cli docker-compose` → moby-engine 29.7.2, docker-cli 29.7.2, docker-compose 5.4.0. **Approved but NOT yet executed** as of this writing. |
| Podman | 5.8.4 present (fallback only; plan uses Docker) |
| System Python | 3.14 — irrelevant; the Dockerfile pins `python:3.11` and all verification runs inside Docker |
| Seed repo clone | `/home/minnix/reeltalk` — commit d37b7f6 (README.md, LICENSE.md verbatim ACRL, HANDOFF.md); remote = github.com/minnixtx/reeltalk |
| Work clone | `/home/minnix/reeltalk-work` — BookWyrm at `afd5ec305`, full history, ~105 MB. **All Phase 1 code work happens here.** |
| Git identity to set (repo-local in reeltalk-work) | `user.name = minnixtx`, `user.email = 61262716+minnixtx@users.noreply.github.com` |
| Sudo | Available. The password was provided in session-1 chat but **must never be written to any file** (including this one). If sudo is needed, ask the owner for it. |

## 4. Decision log (owner decisions — do not re-litigate)

1. **Full rename:** `bookwyrm/`→`reeltalk/`, `celerywyrm/`→`celerytalk/`, `BOOKWYRM_*`→`REELTALK_*`, all user-visible branding, `bw-dev`→`rt-dev`.
2. **Phase 1 = rebrand + running site only.** Film domain model is Phase 2 (designed with owner later).
3. **Keep BookWyrm's full git history** (no orphan repo); reset `VERSION` to `0.1.0`.
4. **Full federation identity rename to "reeltalk"** — all interop string units renamed together (see §7.3). Standard ActivityPub federation with existing BookWyrm instances still works after the rename; only BookWyrm-to-BookWyrm "pure" serialization shortcuts and instance-type detection change.
5. **Install Docker via dnf** (approved; not yet executed).
6. **Deployment simplification is in alpha scope:** merge the two redis containers, remove flower, minimal `.env` + `setup.sh`.
7. Code review before code changes; first alpha must be as simple as possible to self-host, Docker-first.
8. Upstream BookWyrm's AGENTS.md restriction ("Agents must not make contributions or changes") **does not apply** — ReelTalk is a separate project.

## 5. Code-review findings (condensed from three review passes)

### 5.1 Deployment complexity (the self-hosting warts to fix)

- `docker-compose.yml` (218 lines) runs **11 services**: nginx, anubis, certbot, db-backup-job, db (postgres:17), web (gunicorn), redis_activity, redis_broker, celery_worker, celery_beat, flower.
- **Two redis containers are mergeable into one** via DB indexes: DB0 = ActivityPub streams / Django cache / sessions (`REDIS_ACTIVITY_URL`), DB1 = Celery broker. Both currently run `redis-server --requirepass ${...} --appendonly yes` and mount `./redis.conf` — a **dead config file**: it contains `bind 127.0.0.1`, which would break container networking if it were ever actually loaded (the command-line flags override it, but the mount is misleading). Delete the mount and the file.
- **flower** is a monitoring UI with no exposed ports — remove the service, its nginx upstream + location, `FLOWER_*` env vars, and the `flower` dependency. Its imports are cleanly gated (no ungated code references).
- **anubis** (proof-of-work bot proxy in nginx's auth path) is image `ghcr.io/techarohq/anubis:latest` — **unpinned**; pin to a specific release tag.
- **nginx resolves upstream hostnames at config-parse time** (`nginx/server_config` lines ~32–44 declare `upstream web/flower/anubis`). Removing the flower service therefore *requires* removing its `upstream` block (server_config ~:38–40) and its `location /flower` block (`nginx/locations` ~:109–116), or nginx fails to start.
- **Port quirk** in compose nginx service (~line 15): `"${PORT:-443:443}"` — works when PORT is unset, breaks if the user sets `PORT`. Replace with explicit `80:80` and `443:443`.
- **settings.py import-time crash:** `EMAIL_HOST = env("EMAIL_HOST")`, `EMAIL_HOST_USER = env("EMAIL_HOST_USER")`, `EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")` have **no defaults** (verified, settings.py lines ~34–42). Any self-hoster who omits SMTP vars gets a crash at import. Fix: default `"localhost"`, `""`, `""`.
- **`ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", ["*"])`** (~line 105) — insecure default; change to `[DOMAIN]`.
- `.env.example` (170 lines, ~60 vars) is a self-hosting trap: contains dead vars (`FLOWER_PORT`, `EMAIL` — only used by the unused docker-compose-init_letsencrypt.yml) and omits real ones (`USE_S3_FOR_EXPORTS` + 6 `EXPORTS_*` vars, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `TIME_ZONE`). Replace with a minimal file (see §8.4).

### 5.2 Dependency entanglement verdicts (pyproject.toml main group)

- **Cleanly droppable in Phase 1:** `flower`, `opentelemetry-sdk` (imports gated behind `if settings.OTEL_*` in both apps.py files).
- **Entangled — keep for alpha:** `opentelemetry-api` (~8 lines: activitystreams.py, suggested_users.py), `boto3` + `s3_tar` (module-level import chain via models/__init__.py → export job model), `colorthief` (preview_images imported by 4 core model files), `imagekit` + `pilkit` (core-entangled), `bw-file-resubmit` (BookWyrm-specific PyPI package; keep).
- **No dependency removals are required** for Phase 1's deployment simplification except `flower` (+ optionally `opentelemetry-sdk`).

### 5.3 Feature inventory (alpha keeps ALL features — deployment simplification only, no feature removal)

- **Core:** search/connectors (OpenLibrary, Finna, Inventaire, Libris, BookWyrm — note: Gutendex is NOT in this clone), follows/blocks/mutes, reviews/ratings/comments/quotes/boosts (model hierarchy at models/status.py:32; the `book` FK is the Phase 2 swap point), lists + streams, DMs, email, admin, imagekit thumbnails.
- **Deferrable post-alpha (kept in codebase):** importers, export, shelves, groups, TOTP 2FA, PWA, preview images, OTEL.

### 5.4 Federation layer map (what carries into Phase 2 unchanged)

- **Unchanged:** activitypub/signatures.py, views/inbox.py, views/wellknown.py, activitypub/verbs.py, activitypub/person.py, activitypub/ordered_collection.py, utils/redis_store.py, lists_stream.py, antispam.py.
- **Book-coupled (Phase 2 rework):** activitypub/book.py, activitypub/note.py.

### 5.5 Migration risk assessment (why the rename strategy is what it is)

- 312 migration files; 311 contain "bookwyrm". Django couples app label == package name: `apps.py` has `class BookwyrmConfig(AppConfig)` with implicit label = package name. After `git mv bookwyrm reeltalk`, the label becomes `reeltalk`, so **every** migration reference (`to="bookwyrm.X"`, `apps.get_model("bookwyrm", ...)`, FK strings) must be rewritten — a global content sed does exactly this, uniformly.
- Bare-string identifiers dominate: Django conventional table names and index names appear as raw strings in migrations (`bookwyrm_import_job` ×59, `bookwyrm_author` ×28, index names like `bookwyrm_bo_origin__a...`, plus camelCase `bookwyrmUser` and prefix forms like `is_bookwyrm_request`). Piecemeal seds would miss these; a protected blanket replacement catches all of them.
- **No `db_table` overrides exist** — table names are purely conventional, so renaming the strings is safe on a fresh DB (there is no existing production database to migrate; Phase 1 deploys fresh).
- `base_activity.py:328,415` does `apps.get_model(f"bookwyrm.{model_name}")` string lookups — caught by the blanket sed.
- **Do NOT rename:** migration `0243_auto_20260730_0926.py:16` contains the external domain `"bookwyrm.social"` (covered by the protection list, §7.2). Test fixtures use `https://bookwyrm.social/...` URLs — keep (also covered).
- Migration `0142_auto_20220227_1752.py` bakes theme SCSS paths into DB data (`css/themes/bookwyrm-light.scss`, `css/themes/bookwyrm-dark.scss`). The blanket sed rewrites these strings AND the corresponding static files are renamed to match (§7.4) — consistent on a fresh DB.
- Migration `0191_migrate_search_vec_triggers_to_pgtriggers.py:10` does `import_module("bookwyrm.migrations.0077_auto_20210623_2155")` — string-based dynamic import, rewritten consistently by the sed; target file has no bookwyrm in its name.
- **Connector dynamic loading:** `connectors/connector_manager.py:174` does `importlib.import_module(...)` keyed on the DB column `connector_file`, whose value is the string `"bookwyrm_connector"` (set in `management/commands/initdb.py:85`, referenced in connectors/settings.py:6, connector_manager.py:115,135, views/admin/connectors.py:40,47,60). The sed rewrites all string literals consistently and the file is renamed to match (§7.4). Because `initdb` (not a migration) writes the row on fresh setup, consistency holds.
- Test suite: 178 files / ~31.8k lines under bookwyrm/tests/. Only **~7 literal "bookwyrm"/"BookWyrm" string assertions** exist (e.g., tests/views/test_wellknown.py:90 asserts nodeinfo software name; tests/models/test_user_model.py:125 asserts `activity["bookwyrmUser"] == False`). The sed rewrites both sides consistently; the pytest phase confirms.
- **Binary fixture caveat:** `tests/data/bookwyrm_account_export.tar.gz` cannot be content-rewritten by sed. If any test asserts on bookwyrm strings inside it, fix the *assertion* to match the fixture's actual (unchanged) content — do not regenerate the binary.

## 6. Phase 0 — Environment preparation

1. Install Docker (owner-approved): `sudo dnf install moby-engine docker-cli docker-compose`. Verify: `docker --version`, `docker compose version`, and that the daemon runs (`systemctl status docker` / `docker info`). If the user isn't in the `docker` group, either add it (requires re-login) or use sudo for docker commands — prefer adding the current user to the group.
2. In `/home/minnix/reeltalk-work`: set repo-local git identity (`git config user.name minnixtx`, `git config user.email 61262716+minnixtx@users.noreply.github.com`).
3. Confirm clean working tree: `git status` (should be pristine at `afd5ec305`).

## 7. Phase 1 — Rebrand (protected blanket replacement)

Work in `/home/minnix/reeltalk-work`. Strategy: **placeholder-protect upstream URLs → global case-variant seds on all tracked text files minus excluded paths → restore placeholders → git mv filenames to match rewritten references.** This is safer than piecemeal seds because bare Django table/index names, camelCase wire fields, and prefix-suffix identifier forms are pervasive.

### 7.1 Package renames (first)

```bash
git mv bookwyrm reeltalk
git mv celerywyrm celerytalk
```

This changes the Django app label to `reeltalk` (label == package name). Everything else in this phase makes the rest of the tree consistent with that.

### 7.2 Protection list (placeholder BEFORE the seds)

Replace these exact strings with unique placeholders (e.g., `\x01BWDOMAIN\x01`, `\x01BWORG\x01`, `\x01BWDOCS\x01`) in all files, run the seds, then restore. These are upstream references that must survive verbatim:

| String | Where it appears (verified counts) |
|---|---|
| `bookwyrm.social` | migration 0243_auto_20260730_0926.py:16; test fixture URLs (https://bookwyrm.social/book/5988 ×7, /book/5989 ×6, /author/417 ×4, bare domain ×5+) |
| `bookwyrm-social` | github.com/bookwyrm-social/bookwyrm (×75, ×73 with /issues), bookwyrm-social.bookwyrm Docker image ref (README, ×47 in git metadata+README), bookwyrm-social/documentation (.github/pull_request_template.md:29) |
| `joinbookwyrm.com` | https://joinbookwyrm.com/get-involved ×78, /instances/ ×77, docs.joinbookwyrm.com (×6+, CONTRIBUTING.md), mostly in locale/*.po which is excluded anyway |

Also protect any other upstream URL found by: `git grep -hoE "https?://[^\"' )]*bookwyrm[^\"' )]*" | sort -u` — review the list and add anything pointing at upstream (docs, issues, images) to the placeholders.

### 7.3 Global seds (order matters only for readability; patterns don't overlap)

Apply to **all tracked text files** except: `LICENSE.md`, `locale/**` (translations are Crowdin territory — Phase 2 re-sync). Use e.g.:

```bash
git grep -liE "bookwyrm|celerywyrm|bwdev|bw-dev" \
  | grep -vE "^(LICENSE\.md|locale/)" \
  | xargs sed -i \
    -e 's/celerywyrm/celerytalk/g' \
    -e 's/bookwyrm/reeltalk/g' \
    -e 's/BookWyrm/ReelTalk/g' \
    -e 's/Bookwyrm/Reeltalk/g' \
    -e 's/BOOKWYRM_/REELTALK_/g' \
    -e 's/bw-dev/rt-dev/g' \
    -e 's/bwdev/rtdev/g'
```

(Skip binary files — `git grep` with `-I` or filter by extension; the only known binary of interest is the tar.gz fixture, which must NOT be content-modified.)

This single pass rewrites, among everything else, these **verified interop-critical strings** (all renamed as a unit per owner decision #4):

| String | Location | Old → New |
|---|---|---|
| `USER_AGENT` | settings.py:407 | `f"BookWyrm (BookWyrm/{VERSION}; +{BASE_URL})"` → `f"ReelTalk (ReelTalk/{VERSION}; +{BASE_URL})"` |
| `BOOKWYRM_USER_AGENT` | utils/regex.py:14 | `r"\(BookWyrm/[0-9]+\.[0-9]+\.[0-9]+;"` → `REELTALK_USER_AGENT = r"\(ReelTalk/[0-9]+\.[0-9]+\.[0-9]+;"` — **must stay a matching pair with USER_AGENT** (the sed keeps them in sync automatically) |
| nodeinfo software name | views/wellknown.py:83 | `"software": {"name": "bookwyrm", ...}` → `"reeltalk"` |
| `bookwyrmUser` AP wire field | activitypub/person.py:38 | `bookwyrmUser: bool = False` → `reeltalkUser`; assertion in tests/models/test_user_model.py:125 rewritten by the same sed |
| `application_type` check | models/federated_server.py:40,56 | `== "bookwyrm"` → `== "reeltalk"` |
| `software=` broadcast defaults | models/book.py:141; models/import_job.py (bookwyrm_import_job.py pre-rename):479,496 | `"bookwyrm"` → `"reeltalk"` |
| `is_bookwyrm_request()` | views/helpers.py:63–66 (uses the regex); call sites views/feed.py:153, views/outbox.py:25 (`status.to_activity(pure=not is_bookwyrm_request(request))`) | → `is_reeltalk_request` everywhere |
| `connector_file="bookwyrm_connector"` | connectors/settings.py:6; connector_manager.py:115,135 (dynamic `importlib.import_module` at :174); management/commands/initdb.py:85; views/admin/connectors.py:40,47,60 (incl. template context key `"bookwyrm_connectors"`) | → `reeltalk_connector` / `reeltalk_connectors`; file renamed per §7.4 |

Also rewritten by the blanket pass: `class BookwyrmConfig(AppConfig)` in apps.py (→ `ReeltalkConfig`; implicit label follows the package name), all 311 migration files' app references, Django table/index name strings, static asset paths (`css/bookwyrm.scss` etc.), `gunicorn bookwyrm.wsgi:application` in docker-compose.yml, `celery -A celerywyrm ...` commands, and the `0191` dynamic migration import.

### 7.4 File renames (git mv to match rewritten references)

After the seds, every file whose name contained a renamed token must be moved so imports/paths resolve. Known complete list (verify with the catch-all at the end):

- `complete_bwdev.sh` / `.fish` / `.zsh` → `complete_rtdev.*`
- `contrib/systemd/bookwyrm.service` → `reeltalk.service`; `bookwyrm-worker.service` → `reeltalk-worker.service`; `bookwyrm-scheduler.service` → `reeltalk-scheduler.service`
- Inside the (now renamed) `reeltalk/` package:
  - `connectors/bookwyrm_connector.py` → `reeltalk_connector.py` *(semantic note: this connector imports from BookWyrm instances; renaming is intentional uniformity — Phase 2 redoes connectors for films anyway. Its internal `bookwyrm.social` URLs survive via the protection list.)*
  - `importers/bookwyrm_import.py` → `reeltalk_import.py`
  - `models/bookwyrm_export_job.py` → `reeltalk_export_job.py`
  - `models/bookwyrm_import_job.py` → `reeltalk_import_job.py`
  - `migrations/0198_alter_bookwyrmexportjob_export_data.py` → `..._alter_reeltalkexportjob_...`; index migrations `0199_status_bookwyrm_st_remote__06aeba_idx.py`, `0200_status_bookwyrm_st_thread__cf064f_idx.py`, `0201_keypair_bookwyrm_ke_remote__472927_idx.py`, `0202_user_bookwyrm_us_usernam_b2546d_idx.py`, `0203_user_bookwyrm_us_is_acti_972dc4_idx.py`, `0224_book_bookwyrm_bo_remote__43009f_bloom_and_more.py`, `0225_remove_...`, `0226_remove_...`, `0227_edition_bookwyrm_ed_parent__c4f87c_idx_and_more.py`, `0228_remove_user_bookwyrm_us_is_acti_972dc4_idx_and_more.py` → rename each with `bookwyrm`→`reeltalk` in the filename (migration filenames need not match content, but keep them consistent)
  - `static/css/bookwyrm.scss` → `reeltalk.scss`; `static/css/bookwyrm/` (directory of partials) → `static/css/reeltalk/`
  - `static/css/themes/bookwyrm-light.scss` → `reeltalk-light.scss`; `bookwyrm-dark.scss` → `reeltalk-dark.scss` *(must match the paths rewritten in migration 0142)*
  - `static/js/bookwyrm.js` → `reeltalk.js`
  - `tests/connectors/test_bookwyrm_connector.py` → `test_reeltalk_connector.py`
  - `tests/data/bookwyrm.csv` → `reeltalk.csv` *(content is generic — example.com URLs, no bookwyrm strings)*
  - `tests/data/bookwyrm_account_export.tar.gz` → `reeltalk_account_export.tar.gz` *(binary: rename only, NEVER content-modify; see §5.5 caveat)*
  - `tests/importers/test_bookwyrm_import.py` → `test_reeltalk_import.py`; `test_bookwyrm_user_import.py` → `test_reeltalk_user_import.py`
  - `tests/models/test_bookwyrm_export_job.py` → `test_reeltalk_export_job.py`; `test_bookwyrm_import_job.py` → `test_reeltalk_import_job.py`

**Catch-all:** after all moves, run `git ls-files | grep -iE "bookwyrm|bwdev|celerywyrm"` and rename anything remaining (expected: nothing outside `locale/`).

### 7.5 Manual edits (judgment items the seds can't do)

1. **README.md** — replace with an adapted version: ReelTalk branding, fork provenance line ("ReelTalk is a fork of BookWyrm" + link to github.com/bookwyrm-social/bookwyrm), ACRL license notice intact, self-hosting instructions per §8. The seed repo's README in /home/minnix/reeltalk is the starting point.
2. **CONTRIBUTING.md** — currently just points at docs.joinbookwyrm.com; adapt to ReelTalk (keep upstream link as provenance).
3. **CODE_OF_CONDUCT.md, FEDERATION.md** — rebrand to ReelTalk; keep any explicit upstream-attribution lines.
4. **VERSION** file → `0.1.0`.
5. **.github/pull_request_template.md:29** — references bookwyrm-social/documentation (survives via protection); decide whether to keep the upstream docs pointer or point at ReelTalk's future docs. Keep provenance either way.
6. **Settings instance defaults** — check for any default "BookWyrm" instance name / site settings strings that should read "ReelTalk" (the sed handles literal `BookWyrm`; review `manage.py initdb` output paths and SiteSettings defaults).
7. **Dockerfile** — the sed rewrites `COPY bookwyrm /app/bookwyrm` → `COPY reeltalk /app/reeltalk` etc.; verify the two-stage build references are all consistent (mcompileall line, COPY lines).
8. **Do NOT touch:** LICENSE.md (byte-identical), locale/**, any protected upstream URL.

### 7.6 Phase 1 completion check (before committing)

- `git ls-files | grep -icE "bookwyrm|bwdev|celerywyrm"` → only locale/ files remain.
- Content audit: `git grep -inE "bookwyrm|BookWyrm|BOOKWYRM_|celerywyrm|bw-dev|bwdev" -- . ':(exclude)locale' ':(exclude)LICENSE.md'` → every hit must be a protected upstream reference (bookwyrm.social / bookwyrm-social / joinbookwyrm.com) or an intentional provenance line in docs.
- `diff <(git show HEAD:LICENSE.md) LICENSE.md` → empty (byte-identical).

## 8. Phase 2 — Deployment simplification (alpha self-hosting)

Goal: a new self-hoster can go from clone to running site with ~4 commands and one small .env.

### 8.1 docker-compose.yml edits

1. **Merge redis_activity + redis_broker into one `redis` service** (image redis:7.2.1, single volume `redis_data`):
   - One password: `REDIS_PASSWORD`.
   - DB0 = app (streams/cache/sessions), DB1 = Celery broker.
   - Update web's `depends_on` and celery_worker/celery_beat's `depends_on` to the merged service.
   - Remove both `./redis.conf:/etc/redis/redis.conf` mounts (dead config — see §5.1) and delete the `redis.conf` file from the repo.
2. **Remove flower entirely:** service block (~:184–208), its volumes entry, plus:
   - `nginx/server_config` upstream block (~:38–40) — required, nginx parses upstreams at config load;
   - `nginx/locations` flower location (~:109–116);
   - `FLOWER_PORT` / `FLOWER_USER` / `FLOWER_PASSWORD` from .env handling and celerytalk/settings.py (`FLOWER_PORT = env.int("FLOWER_PORT", 8888)` at line 37 is dead).
3. **Pin anubis** to a specific release tag (replace `ghcr.io/techarohq/anubis:latest`).
4. **Fix nginx ports:** replace `"${PORT:-80}:80"` / `"${PORT:-443:443}"` with explicit `80:80` and `443:443`.
5. Result: **9 services** (nginx, anubis, certbot, db-backup-job, db, web, redis, celery_worker, celery_beat).

### 8.2 Settings changes (reeltalk/settings.py)

Verified current code → change:

```python
# lines ~34-42 (email block) — fix import-time crash for self-hosters without SMTP:
EMAIL_HOST = env("EMAIL_HOST")                    # → env("EMAIL_HOST", "localhost")
EMAIL_HOST_USER = env("EMAIL_HOST_USER")          # → env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")  # → env("EMAIL_HOST_PASSWORD", "")
# (EMAIL_BACKEND/PORT/USE_TLS/USE_SSL/SENDER_* already have safe defaults)

# line ~105 — insecure default:
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", ["*"])  # → env.list("ALLOWED_HOSTS", [DOMAIN])

# lines ~247-255 (REDIS_ACTIVITY_HOST/PORT/PASSWORD/DB_INDEX → REDIS_ACTIVITY_URL):
# collapse to a single REDIS_URL (or REDIS_PASSWORD + fixed host/port/db) matching the merged container;
# DB index 0 for app data.
```

celerytalk/settings.py lines ~6–21 (`REDIS_BROKER_*` → `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`): point at the same redis container, DB index 1, single password.

### 8.3 Dependency cleanup (pyproject.toml)

Remove `flower` from the main group (and `opentelemetry-sdk` if desired — gated imports make it safe). Keep everything else (§5.2).

### 8.4 Minimal .env.example + setup.sh

Replace the 170-line .env.example with a minimal file (~15 active lines):

```ini
# --- Required (setup.sh generates the three secrets) ---
DOMAIN=your-instance.example.com
SECRET_KEY=
POSTGRES_PASSWORD=
REDIS_PASSWORD=

# --- HTTPS / Let's Encrypt (NGINX_SETUP=http for local dev) ---
# NGINX_SETUP=https
# CERTBOT_EMAIL=you@example.com

# --- Email (optional; safe defaults let the site run without SMTP) ---
# EMAIL_HOST=localhost
# EMAIL_PORT=587
# EMAIL_HOST_USER=
# EMAIL_HOST_PASSWORD=
# EMAIL_SENDER_NAME=admin
# EMAIL_SENDER_DOMAIN=          # defaults to DOMAIN

# --- Optional overrides ---
# POSTGRES_SHM_SIZE=128mb
# DATA_UPLOAD_MAX_MEMORY_MiB=100
# TIME_ZONE=UTC
```

`setup.sh` (pattern lifted from the existing `bw-dev create_secrets`, which becomes `rt-dev`): read `.env`; generate `SECRET_KEY` (Django-compatible), `POSTGRES_PASSWORD`, `REDIS_PASSWORD` if empty; prompt for `DOMAIN` if unset; prompt for `CERTBOT_EMAIL` when `NGINX_SETUP=https`. Non-interactive-friendly (no prompts if all values present).

**Resulting self-host flow:** clone → `cp .env.example .env` → `./setup.sh` → `docker compose up -d` (certbot-before-nginx ordering is already enforced by depends_on) → `docker compose run --rm web python manage.py createsuperuser`.

## 9. Phase 3 — Verification checklist

Run in order; report results faithfully (never claim green on red).

1. **Rename audit** (§7.6): filename grep + content grep + LICENSE.md byte-diff.
2. **Compose validity:** `docker compose config` (catches YAML/env errors after the service merges/removals).
3. **Django check:** `docker compose run --rm web python manage.py check`.
4. **Fresh-DB migrations:** with a clean pgdata volume, full `migrate` + `initdb` must succeed (this is where migration-string inconsistencies would surface).
5. **Run the stack:** `docker compose up -d`; all 9 services healthy; then:
   - `curl` the homepage → ReelTalk branding in title/meta;
   - `/nodeinfo/2.0/` (or the wellknown endpoint) → `"software": {"name": "reeltalk", ...}`;
   - verify the User-Agent sent on outbound requests matches the new `ReelTalk (ReelTalk/x.y.z; ...)` format.
6. **Full test suite:** `docker compose run --rm web python manage.py test` (or the project's pytest invocation — check pyproject/CI for the canonical command). Expect ~7 literal string assertions to need updating (test_wellknown.py:90 nodeinfo name, test_user_model.py:125 `bookwyrmUser`, etc.) — the sed should have rewritten most consistently; fix any stragglers. Watch specifically for failures involving the binary tar.gz fixture (§5.5): fix assertions to match actual fixture content, never regenerate the binary.
7. **Static assets:** confirm `collectstatic` succeeds and no template references a missing (old-named) asset — the theme SCSS renames + migration 0142 paths are the main risk area; check compiled themes in the running container.

## 10. Phase 4 — Commit & push

1. Two commits on `main` in /home/minnix/reeltalk-work:
   - `Rebrand BookWyrm fork as ReelTalk` (all of Phase 1)
   - `Simplify deployment for alpha self-hosting` (all of Phase 2)
2. Add the fork remote and push: `git remote add fork https://github.com/minnixtx/reeltalk.git` (or set origin), then push `main`.
   - **This is a force-push** (the seed repo's d37b7f6 commit — README/LICENSE/HANDOFF — is replaced by the full BookWyrm history + rebrand commits, per owner decision #3). The seed README content is superseded by the adapted README; LICENSE.md is already byte-identical in the work tree; HANDOFF.md is intentionally dropped ("delete once Phase 1 complete").
   - **Ground rule: obtain explicit owner confirmation at the moment of pushing.** No force-push without it.

## 11. Ground rules for the executing session

1. **No force-push to minnixtx/reeltalk without explicit owner confirmation at that moment** (even though GitHub access is pre-authorized).
2. **No Phase 2 design decisions** — film domain model, metadata sources, artwork: none of it. Phase 1 is rebrand + deployment only.
3. **LICENSE.md stays byte-identical; attribution never stripped.** Verify with a diff before committing.
4. **Never write the sudo password (or any secret) into files**, including docs, .env, or commit messages. Ask the owner when sudo is needed.
5. **Report verification faithfully** — if a check fails, say so with output; don't paper over it.
6. Keep upstream git history intact (no orphaning, no history rewriting beyond normal commits).

## 12. Phase 2 preview (NOT in scope for this execution — context only)

- **Film domain model** replacing the Work/Edition/Author/Shelf hierarchy: the `book` FK on the status model (models/status.py:32 hierarchy) is the swap point; activitypub/book.py and note.py are the book-coupled federation pieces to rework.
- **TMDB metadata** as the primary film data source, replacing the book connectors (OpenLibrary/Finna/Inventaire/Libris/BookWyrm).
- **Custom artwork** replacing BookWyrm's placeholder/wyrm imagery.
- **Public instance deployment** of the alpha.
- **Crowdin re-sync** for translations (locale/** is deliberately untouched in Phase 1; it still contains BookWyrm strings and will be re-pointed at ReelTalk's Crowdin project).
- Design the domain model **with the owner** before implementing.

---

*End of plan. Execution order: §6 → §7 → §8 → §9 → §10.*
