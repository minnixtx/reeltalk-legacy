# ReelTalk — Progress Tracker

**Last updated:** 2026-08-24
**Audience:** any new session picking up this project. Read this first, then `PLAN.md` (the historical Phase 1 execution plan) if you need the original reasoning.

---

## 1. What this project is

**ReelTalk** is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) (base commit `afd5ec305`) retooled as a federated (ActivityPub) social site for **film reviews**. The owner is a B-movie/cult-film enthusiast; the name is final.

- Fork repo: https://github.com/minnixtx/reeltalk (GitHub account `minnixtx`)
- **License:** Anti-Capitalist Software License v1.4 (© 2020 Mouse Reeve) — *not* AGPL. Hard rules:
  - `LICENSE.md` must stay **byte-identical** to upstream; never rename or edit it.
  - Attribution to BookWyrm / Mouse Reeve is never stripped; upstream references (`bookwyrm.social`, `github.com/bookwyrm-social/*`, `joinbookwyrm.com`) are intentional provenance links — do not "fix" them.
  - Any move toward commercial use must stop and be flagged to the owner (ACRL forbids it).

## 2. Current state (as of 2026-08-24)

| Area | State |
|---|---|
| Phase 1 (rebrand + deployment simplification) | ✅ Done, pushed, verified (full test suite green ×2) |
| Pre-Phase-2 changes (no HTTPS, no anubis, :3030 endpoint, no CONTRIBUTING) | ✅ Done, pushed (owner-directed, 2026-08-23) |
| CSRF trusted-origins fix | ✅ Done, pushed (2026-08-24) |
| Local instance | ✅ Running and **initialized**: DB migrated, `initdb` seeded, admin account created via the `/setup` wizard (2 users exist), `install_mode=false`. Reachable at **http://192.168.1.138:3030** |
| Phase 2 (film domain model) | ⬜ Not started — to be **designed with the owner** before implementation |

## 3. Commit history (`main`)

```
fea8546f7 Allow CSRF_TRUSTED_ORIGINS override for non-DOMAIN access origins
776ae008a Drop HTTPS/Let's Encrypt and anubis; expose plain-HTTP endpoint on :3030
22202ff2d Simplify deployment for alpha self-hosting        ← Phase 1 (commit 2/2)
c4fa83cc2 Rebrand BookWyrm fork as ReelTalk                 ← Phase 1 (commit 1/2)
afd5ec305 New Crowdin updates (#4053)                       ← upstream BookWyrm base
```

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

## 5. What still needs to be done

### Immediate / local
- **Nothing blocking.** The instance is initialized and clickable at http://192.168.1.138:3030 (login page). The owner was actively using it when work paused.
- If the host's LAN IP changes again: update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in the live `.env`, then `docker compose up -d && docker compose restart nginx` (see §7 quirks).

### Phase 2 — film domain model (DESIGN WITH THE OWNER FIRST; no solo design decisions)
From PLAN.md §12, the agreed preview:
- Replace the Work/Edition/Author/Shelf book hierarchy with a film domain model (titles, years, cast, ratings). The `book` FK on the status model (`reeltalk/models/status.py`, ~line 32) is the swap point.
- **TMDB** as the primary film metadata source, replacing the book connectors (OpenLibrary/Finna/Inventaire/Libris/BookWyrm).
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
- **Green baseline:** 1357 passed / 1 skipped / 1 xfailed (~4 min with `-n 3`).

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
