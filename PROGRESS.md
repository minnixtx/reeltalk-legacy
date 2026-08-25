# ReelTalk — Progress Tracker

**Last updated:** 2026-08-25
**Audience:** any new session picking up this project. Read this first, then `PLAN.md` (the historical Phase 1 execution plan) if you need the original reasoning.

---

## 1. What this project is

**ReelTalk** is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) (base commit `afd5ec305`) retooled as a federated (ActivityPub) social site for **film reviews**. The owner is a B-movie/cult-film enthusiast; the name is final.

- Fork repo: https://github.com/minnixtx/reeltalk (GitHub account `minnixtx`)
- **License:** Anti-Capitalist Software License v1.4 (© 2020 Mouse Reeve) — *not* AGPL. Hard rules:
  - `LICENSE.md` must stay **byte-identical** to upstream; never rename or edit it.
  - Attribution to BookWyrm / Mouse Reeve is never stripped; upstream references (`bookwyrm.social`, `github.com/bookwyrm-social/*`, `joinbookwyrm.com`) are intentional provenance links — do not "fix" them.
  - Any move toward commercial use must stop and be flagged to the owner (ACRL forbids it).

## 2. Current state (as of 2026-08-25)

| Area | State |
|---|---|
| Phase 1 (rebrand + deployment simplification) | ✅ Done, pushed, verified (full test suite green ×2) |
| Pre-Phase-2 changes (no HTTPS, no anubis, :3030 endpoint, no CONTRIBUTING) | ✅ Done, pushed (owner-directed, 2026-08-23) |
| CSRF trusted-origins fix | ✅ Done, pushed (2026-08-24) |
| Local instance | ✅ Running and **initialized**: DB migrated, `initdb` seeded, admin account created via the `/setup` wizard (2 users exist), `install_mode=false`. Reachable at **http://192.168.1.138:3030** |
| Phase 2 — milestone 1 (UI rebrand books→films + binary film shelf model) | ✅ Done, committed, pushed, verified live (full test suite green: 1332 passed) |
| Phase 2 — remainder (film domain model, TMDB importer/connector, artwork, public deploy) | ⬜ Not started — to be **designed with the owner** before implementation |

## 3. Commit history (`main`)

```
(this commit) Rework shelves into a binary film model; rebrand UI from books to films   ← Phase 2 milestone 1 (commit 2/2)
c799e9734 Remove barcode reader, code of conduct, reading goals, Patreon footer          ← Phase 2 milestone 1 (commit 1/2)
9c9363298 Add progress tracker for new sessions
fea8546f7 Allow CSRF_TRUSTED_ORIGINS override for non-DOMAIN access origins
776ae008a Drop HTTPS/Let's Encrypt and anubis; expose plain-HTTP endpoint on :3030
22202ff2d Simplify deployment for alpha self-hosting        ← Phase 1 (commit 2/2)
c4fa83cc2 Rebrand BookWyrm fork as ReelTalk                 ← Phase 1 (commit 1/2)
afd5ec305 New Crowdin updates (#4053)                       ← upstream BookWyrm base
```

(The top line's hash is the commit that contains this file — a commit cannot record its own hash.)

The full BookWyrm history is preserved under the rebrand commits (owner decision: no orphan repo). An earlier seed commit (`d37b7f6`, README/LICENSE/HANDOFF only) was replaced by a force-push with explicit owner approval — it no longer exists on the remote.

## 4. What has been done

### Phase 1 (executed 2026-08-22 per PLAN.md)
- **Full rebrand** via protected blanket replacement: `bookwyrm/`→`reeltalk/`, `celerywyrm/`→`celerytalk/`, `BOOKWYRM_*`→`REELTALK_*`, all user-visible branding, migration strings, wire fields (`reeltalkUser`), nodeinfo software name, user agent. Upstream URLs and `LICENSE.md` protected throughout.
- **Deployment simplification:** merged the two redis containers into one (DB0 = app/streams/cache, DB1 = Celery broker), removed flower, fixed import-time crash on missing SMTP vars, `ALLOWED_HOSTS` default tightened to `[DOMAIN]`, minimal `.env.example` + `setup.sh` (secret generation).
- **Verification:** rename audit clean (only `locale/**` retains BookWyrm strings — Crowdin re-sync is a Phase 2 item), LICENSE byte-identical, compose valid, full test suite green: **1357 passed / 1 skipped / 1 xfailed** (re-run and confirmed again 2026-08-23).

### Pre-Phase-2 changes (owner-directed, 2026-08-23)
- **No HTTPS/Let's Encrypt in the project.** TLS termination is the operator's responsibility. Removed: certbot service, `docker-compose-init_letsencrypt.yml`, `nginx/https.conf`, `nginx/ssl_bootstrap`, daily cert-reload script, `rt-dev init_ssl`, all `NGINX_SETUP`/`CERTBOT_*` config.
- **Plain-HTTP endpoint on port 3030** (`WEB_PORT` env override). The operator points their own reverse proxy at `<host>:3030` and forwards `X-Forwarded-Proto: https`. Nginx now passes the real protocol through (`$scheme`) instead of hardcoding `https`.
- **Anubis bot protection removed entirely.** Diagnosis: nginx's hardcoded `X-Forwarded-Proto https` made anubis set its challenge cookies as `Secure`, which browsers reject over plain HTTP on non-localhost hosts — and anubis's default policy guaranteed a proof-of-work challenge for every real browser (Mozilla/Opera UA = +10 weight ≥ threshold). IP-based access was permanently blocked. Owner approved removal after the diagnosis; `/robots.txt` is served by Django's own view now.
- **CONTRIBUTING.md removed.** `AGENTS.md` states all code contributions come from the project owner until the project reaches a confirmed working state.
- Stack reduced to **7 services**: nginx, web, db, redis, celery_worker, celery_beat, db-backup-job.

### CSRF fix (2026-08-24)
`CSRF_TRUSTED_ORIGINS` was hardcoded to `[BASE_URL]`, which with `DOMAIN=localhost` is only `http://localhost:80` — so form POSTs from any other origin (e.g. the LAN IP) were 403'd by Django's Origin check, blocking the setup wizard. It is now env-overridable (default unchanged), documented in `.env.example`, and set in the live `.env`.

### Local instance initialization (2026-08-23/24)
- Migrations applied (the web image's `/entrypoint.sh` auto-runs migrations + collectstatic on every container start — no manual step needed).
- `manage.py initdb` seeded: 4 permission groups, permissions, 3 book connectors, safe-link domains, SiteSettings.
- Owner completed the web `/setup` wizard (created admin account; a second user also exists). `install_mode=false`, so the site now serves normally at the root URL.

### Phase 2 — first milestone (executed 2026-08-25)
Owner's driving premise: **this is a book-reading site being converted into a film-watching site** — every change must read as consistent with that. Owner supplied a 13-item list; four design questions were settled up front via owner decision (see §8):

1. Exactly **3 shelf tabs** on the user's films page: All films / Want to Watch / Watched — **no** "Watching"/in-progress tab (the film model is binary).
2. **Clean up existing users' default shelves in the local DB** (migration 0246) rather than leaving legacy shelves behind.
3. **TMDB import: rename now, build later** — the UI says "Import Films" and points at a TMDB export; the actual importer lands with the film catalog/TMDB connector milestone.
4. **Focused string pass only** — pages touched by the 13-item list plus visible chrome; deep book-page wording (detail pages, etc.) is deferred to the domain-model milestone.

What was done, in two commits:

**Commit 1/2 (`c799e9734`) — removals:**
- **Barcode reader** removed end-to-end (nav button, `Isbn` view/routes, ISBN search modal templates, scss, tour step). The underlying book-search machinery is kept for now.
- **Code of Conduct** removed completely (view, route, footer link, template, test).
- **Reading Goals** removed completely (`AnnualGoal` model + migration 0245 dropping the table, `show_goal` user field, goal views/routes/forms/templates, export/import of goals, tour step). "No one sets a goal for how many films they want to watch."
- **"Support ReelTalk on Patreon" footer** removed.

**Commit 2/2 — binary film shelf model + rebrand:**
- **Default shelves are now exactly two:** `to-read` → displayed **"Want to Watch"**, `read` → displayed **"Watched"** (`create_shelves`, `SHELF_NAMES`). New users get only these two.
- **Migration 0246 (data):** renames existing users' default shelves ("To Read"→"Want to Watch", "Read"→"Watched") and deletes their `reading` / `stopped-reading` shelves (books on them are simply un-shelved — there is no watching state).
- **Custom shelves removed from the UI:** "+ Create Shelf" button, create/edit/delete shelf views, routes, forms (`ShelfForm`), templates all gone. The `Shelf` model itself is **kept** — it's a federated ActivityPub OrderedCollection and federation safety means we don't remove the wire type; only user-facing custom-shelf management is gone.
- **Shelve controls reduced to binary:** shelve button/dropdown and shelf selector now offer only Want to Watch / Watched (plus unshelve). `next_shelf` chain: to-read → read → complete (`get_next_shelf`).
- **ReadingStatus reduced to `want` + `finish`:** `/reading-status/start` and `/stop` views removed; 4 orphaned templates deleted (`reading_progress/start.html`, `reading_progress/stop.html`, both reading modals). Direct URLs no longer resurrect a "Currently Reading" shelf.
- **Importers remapped so removed shelves can never be resurrected:** base importer guesses send in-progress/abandoned/stopped-reading titles to `to-read` ("anything not watched lands on Want to Watch"); OpenReads and LibraryThing overrides do the same; `upsert_shelves` maps legacy export shelf names ("To Read"/"Currently Reading"/"Stopped Reading"→`to-read`, "Read"→`read`) onto the current defaults instead of creating duplicate custom shelves.
- **String pass (books→films) on visible chrome:** nav bar and profile sidebar "Your Books"→"Your Films"; profile tab "Books"→"Films"; timeline display name "Books Timeline"→"Films Timeline" (internal key `"books"` kept — it's a data identifier, not UI text); import page "Import Books"→"Import Film List" with TMDB export as the described source; guided tours and search placeholders updated.
- **Tests:** ~25 tests deleted with the removed features; remaining tests updated to the binary model (shelf counts 4→2, names, importer expectations, export CSV bytes). Full CI-faithful suite: **1332 passed / 1 skipped / 1 xfailed** (baseline was 1357 before removals).

**Intentionally kept (federation safety / deferred):** `handle_reading_status` still maps all 4 legacy shelf identifiers for inbound remote activity; `Shelf` model constants unchanged; ISBN/book-search machinery and book connectors untouched — all of that gets reworked when the film domain model lands.

## 5. What still needs to be done

### Immediate / local
- **Nothing blocking.** The instance is initialized and clickable at http://192.168.1.138:3030 (login page). The owner was actively using it when work paused.
- If the host's LAN IP changes again: update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in the live `.env`, then `docker compose up -d && docker compose restart nginx` (see §7 quirks).

### Phase 2 — remainder (DESIGN WITH THE OWNER FIRST; no solo design decisions)
Milestone 1 (UI rebrand + binary shelf model, §4) is done. What remains, from PLAN.md §12 plus the owner's 13-item list:
- **Build the TMDB import path** — the UI already says "Import Films" and describes a TMDB export; the actual importer + TMDB connector must be built to make it real (owner decision: rename now, build later).
- Replace the Work/Edition/Author book hierarchy with a film domain model (titles, years, cast, ratings). The `book` FK on the status model (`reeltalk/models/status.py`, ~line 32) is the swap point. This milestone also owns the **deep book-page wording** deferred by the focused string pass.
- **TMDB** as the primary film metadata source, replacing the book connectors (OpenLibrary/Finna/Inventaire/Libris/BookWyrm). The ISBN/book-search machinery kept in milestone 1 gets reworked or dropped here.
- Custom ReelTalk artwork replacing BookWyrm's placeholder/wyrm imagery.
- Rework the book-coupled federation pieces: `reeltalk/activitypub/book.py` and `note.py`.
- Re-point `locale/**` at a ReelTalk Crowdin project (still contains BookWyrm strings).
- Public instance deployment of the alpha (operator's own TLS proxy in front of :3030).

### Housekeeping / known items
- The seed repo at `/home/minnix/reeltalk` holds stale local history (diverged from the remote after the force-push). Re-clone or delete if a clean copy is wanted.
- With `DOMAIN=localhost`, `BASE_URL` computes to `http://localhost:80` — cosmetic oddity (shown in instance settings, used in the outbound user agent). Setting a real `DOMAIN` when deploying for real fixes it; update `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` accordingly.
- Real-domain deployment checklist: set `DOMAIN`, point your TLS proxy at `<host>:3030` forwarding `X-Forwarded-Proto: https`, keep `WEB_PORT` in mind for firewall rules.

## 6. Environment facts

| Fact | Value |
|---|---|
| Machine | Fedora 44, KDE, HP Z2 G4. Docker installed via dnf (moby-engine 29.7.2, docker-cli 29.7.2, docker-compose 5.4.0) — no third-party repo |
| LAN | **Hardwired as of 2026-08-24 → `192.168.1.138`** (was Wi-Fi `192.168.1.58`; hardwired after repeated Wi-Fi disconnects). Owner's laptop: `192.168.1.185` |
| Sudo | Available. Ask the owner for the password when needed — **never write it to any file** |
| System Python | 3.14 (irrelevant; everything runs in Docker, image pins python:3.11) |
| Work clone | `/home/minnix/reeltalk-work` — **all code work happens here** |
| Remotes | `fork` = github.com/minnixtx/reeltalk (**push target**); `origin` = bookwyrm-social/bookwyrm (upstream — **never push**) |
| Seed repo | `/home/minnix/reeltalk` — stale local history only, see §5 |

### Live `.env` (untracked, in reeltalk-work — secrets omitted here on purpose)
```
DOMAIN=localhost
ALLOWED_HOSTS=localhost,192.168.1.138
CSRF_TRUSTED_ORIGINS=http://localhost:3030,http://192.168.1.138:3030
# + generated SECRET_KEY / POSTGRES_PASSWORD / REDIS_PASSWORD, WEB_PORT unset (default 3030)
```

## 7. Operations runbook (for a new session)

### Stack basics
```sh
cd /home/minnix/reeltalk-work
docker compose up -d            # start / apply config changes
docker compose down             # stop (volumes preserved)
docker compose logs -f web      # inspect a service
```
- 7 services: nginx (:3030), web (gunicorn :8000 internal), db (postgres:17), redis (7.2.1, single container), celery_worker, celery_beat, db-backup-job (one-shot).
- The web image **auto-runs migrations + collectstatic on start** (`/entrypoint.sh`) — after `up -d`, wait for the web healthcheck before curling.

### Known host/stack quirks (all verified, all real)
1. **Nginx upstream DNS cache:** nginx resolves `web:8000` at startup only. After ANY web container recreation (rebuild, `.env` change), run `docker compose restart nginx` — otherwise the stack 502s with an *empty* nginx error log.
2. **SELinux:** ad-hoc docker bind mounts on this Fedora host MUST use the `:z` label or containers get Permission denied even as root.
3. **IPv6 docker-proxy quirk:** IPv6 `[::1]` through docker-proxy resets HTTP connections (raw TCP is fine, nginx never sees the request). Host networking issue, not app config — test with `curl -4`.
4. Container writes to mounted dirs leave root-owned files (pycache) — clean up with sudo if they accumulate.

### Running the test suite (CI-faithful flow)
The Docker image **excludes tests** (upstream `.dockerignore` has `**/tests`). Use a temp source copy:
```sh
cd /home/minnix/reeltalk-work
TMP=$(mktemp -d /tmp/rt-tests.XXXXXX)
tar --exclude=.git -cf - . | tar -C "$TMP" -xf -
docker compose run --rm -v "$TMP:/src:z" -w /src web sh -c \
  "python manage.py check && python manage.py compile_themes && python manage.py collectstatic --no-input && pytest -n 3"
```
- Skipping `compile_themes` + `collectstatic` causes ~237 spurious failures (manifest_strict ValueError on theme CSS).
- **Green baseline:** 1332 passed / 1 skipped / 1 xfailed (~3 min with `-n 3`) — as of Phase 2 milestone 1 (2026-08-25; ~25 tests removed with the barcode/conduct/goal/custom-shelf features).

### After changing app code
`docker compose up -d --build` (rebuilds the web image), then `docker compose restart nginx` (quirk #1), then wait for web healthy.

## 8. Owner decision log (do not re-litigate)

1. **Full rename** of all BookWyrm identifiers/branding; upstream URLs and LICENSE protected.
2. **Keep BookWyrm's full git history** (no orphan repo); `VERSION` reset to 0.1.0.
3. **Force-push approved** for the Phase 1 handoff (replaced the seed commit).
4. **No HTTPS/Let's Encrypt in the project** (2026-08-23): plain-HTTP endpoint on :3030; the operator terminates TLS with their own proxy.
5. **Anubis removed** (2026-08-23, after cookie-wall diagnosis).
6. **CONTRIBUTING.md removed**; the owner is the sole code contributor until a confirmed working state (recorded in AGENTS.md).
7. **Phase 1 = rebrand + running site only.** The film domain model is Phase 2 and will be **designed with the owner** — no Phase 2 design decisions unilaterally.
8. Upstream BookWyrm's AGENTS.md restriction on agent contributions does **not** apply to ReelTalk (separate project) — but see #6 for the current owner-only policy.
9. **Binary film shelf model** (2026-08-25): exactly 3 tabs — All films / Want to Watch / Watched. **No "Watching"/in-progress tab.** A film is either watched or not; there is no watching state.
10. **Clean up existing users' shelves in the local DB** (2026-08-25): migration 0246 renames default shelves to the film names and drops `reading`/`stopped-reading` shelves rather than leaving legacy data behind.
11. **TMDB import: rename now, build later** (2026-08-25): the UI is rebranded to "Import Films" / TMDB export immediately; the actual importer and TMDB connector are built in a later milestone once the film catalog exists.
12. **Focused string pass for Phase 2 milestone 1** (2026-08-25): books→films wording was applied to the pages named in the owner's list plus visible chrome only; deep book-page wording is deferred to the domain-model milestone.
