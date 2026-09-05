# ReelTalk — Build Handoff

This file is context for the AI session taking over on the **build server**. It summarizes what was decided and done in the first session (on a different machine), and what to do next. **Delete this file once Phase 1 is complete.**

## 1. What the project is

**ReelTalk** is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) — the open-source, ActivityPub-based (federated) social network for books — retooled as a federated social site for **reviewing films**.

- The owner is a **B-movie and cult film enthusiast** (midnight shows, double features, grindhouse, VHS era). Lean into that in copy and design choices.
- Name rationale: "ReelTalk" is a pun on **"real talk"** — honest conversation — with *reel* anchoring it to film. The name was chosen by the owner after several brainstorming rounds; do not revisit it.
- Core values the name/brand should carry: **user-driven, film-related, free and open**.

## 2. What is already done (session 1)

GitHub repo exists and is public: **https://github.com/minnixtx/reeltalk** (owner GitHub account: `minnixtx`).

Current contents of `main` (single commit `d37b7f6`, "Initial commit: ReelTalk project seed"):
- `README.md` — project description, status, roadmap (drafted in session 1; adapt it when the fork lands)
- `LICENSE.md` — BookWyrm's license text, verbatim (see §3)

No code exists yet. The full BookWyrm clone/rename has **not** been started anywhere.

## 3. License — read this before touching anything

BookWyrm is **NOT** AGPL. Its `LICENSE.md` is the **Anti-Capitalist Software License (v1.4)**, Copyright © 2020 Mouse Reeve. Key conditions:

1. The copyright notice and license text **must be included in all copies or modified versions** → keep `LICENSE.md` verbatim in the fork; never strip attribution to Mouse Reeve / BookWyrm.
2. Permitted users: an individual laboring for themselves, a non-profit, an educational institution, or a worker-owned cooperative with equal equity/vote. (The owner qualifies as an individual.)
3. **Not permitted:** use by for-profit ("capitalist") organizations, or by law enforcement / military. If the project ever heads commercial, stop and flag this to the owner.

## 4. Decisions already made by the owner (do not re-litigate)

| Decision | Choice |
|---|---|
| Rename depth | **Full rename**: packages `bookwyrm/` → `reeltalk/`, `celerywyrm/` → `celerytalk/`, env prefix `BOOKWYRM_*` → `REELTALK_*`, all user-visible branding |
| Phase 1 scope | **Rebrand + running site only.** The book data model (Work/Edition/Author/Shelf) stays intact. Film-domain conversion is Phase 2, not started, and needs its own design pass with the owner |
| Git history | Keep BookWyrm's **full history** (clone it; do not make an orphan repo) — required for license provenance |
| Versioning | Reset the `VERSION` file to `0.1.0` for the fork |

## 5. BookWyrm repo structure (verified against upstream)

Top level of `bookwyrm-social/bookwyrm`:

- `bookwyrm/` — the Django app (settings.py, models/, views/, templates/, tests/, management commands)
- `celerywyrm/` — Celery tasks package (**second package to rename**)
- `manage.py` — sets `DJANGO_SETTINGS_MODULE=bookwyrm.settings`
- `pyproject.toml`, `pytest.ini`, `gunicorn.conf.py`, `entrypoint.sh`, `Dockerfile`
- `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose-init_letsencrypt.yml`, `docker-compose-upgrade-db.yml`
- `.env.example`, `.env.dev.example` (env vars use the `BOOKWYRM_*` prefix)
- `bw-dev` — dev helper script, plus `complete_bwdev.{sh,fish,zsh}` completions
- `bump-version.sh`, `VERSION`
- `.github/workflows/` — CI (references the upstream org/repo; update to `minnixtx/reeltalk`)
- `nginx/`, `static/` (incl. PWA manifest with name/short_name), `images/` (logo art), `locale/` (Crowdin translations, `crowdin.yml`)
- Docs: `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `FEDERATION.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Misc dirs: `anubis/`, `contrib/`, `dev-tools/`, `exports/`, `postgres-docker/`, `updates/`

## 6. Phase 1 plan (execute on the build server)

### 6.1 Setup
1. Check the build server has: git, Python matching BookWyrm's requirement (check upstream `pyproject.toml`), Docker (preferred for a full local run incl. Postgres + Redis). If no Docker, fall back to venv + local Postgres/Redis and say so in your report.
2. The build server needs its own git auth to push (e.g. owner runs `gh auth login`, or existing credentials). Do not ask the owner to paste tokens into chat.
3. `git clone https://github.com/bookwyrm-social/bookwyrm` into a working directory (e.g. `~/reeltalk`).

### 6.2 Rename (mechanical, scripted)
1. `git mv bookwyrm reeltalk` and `git mv celerywyrm celerytalk`
2. Global text replacement across tracked files — handle each case variant **separately**:

   | From | To |
   |---|---|
   | `bookwyrm` (imports, paths) | `reeltalk` |
   | `BookWyrm` (display strings) | `ReelTalk` |
   | `BOOKWYRM_` (env prefix) | `REELTALK_` |
   | `celerywyrm` / `Celerywyrm` | `celerytalk` / `Celerytalk` |
   | `bw-dev`, `complete_bwdev.*` | `rt-dev`, `complete_rtdev.*` |

3. **Do NOT replace:**
   - Upstream attribution links (the `bookwyrm-social` org URLs in LICENSE/CODE_OF_CONDUCT credits) — provenance must stay visible
   - `locale/*.po` translation files — stale entries are harmless; they regenerate via Crowdin later
   - `images/` logo assets — BookWyrm's wyrm art stays as placeholder (custom ReelTalk artwork is Phase 2)

### 6.3 Hand edits (not sed-able)
- `README.md` — adapt the existing draft from `minnixtx/reeltalk` (it is in this repo); update status once Phase 1 lands
- `AGENTS.md`, `CONTRIBUTING.md`, `FEDERATION.md` — BookWyrm → ReelTalk references
- PWA manifest in `static/` — name / short_name / theme metadata
- `reeltalk/settings.py` — instance-name default ("BookWyrm Social" → "ReelTalk")
- `.github/workflows/*` — repo references to the new location
- Reset `VERSION` to `0.1.0`

### 6.4 Verification (all must pass before reporting done)
1. **Grep audit**: no remaining `bookwyrm|BookWyrm|BOOKWYRM_|celerywyrm|bw-dev` outside the intentionally-kept files (LICENSE attribution, locale/, images/)
2. `python manage.py check` passes
3. Migrations apply cleanly on a fresh dev DB
4. Server starts (docker-compose.dev.yml preferred); homepage renders with ReelTalk branding (curl it)
5. `pytest` — run the suite; fix string-assertion tests that referenced "BookWyrm"

### 6.5 Commit + push
1. Single rebrand commit on top of BookWyrm history, e.g. `Rebrand BookWyrm fork as ReelTalk (Phase 1)`
2. **Pushing to `minnixtx/reeltalk` requires a force-push** — the seed repo's one commit (`d37b7f6`) has unrelated history; the fork replaces it. The seed files' content is preserved (README adapted, LICENSE kept verbatim). **This is destructive on a public repo: get explicit owner confirmation before `git push --force`.**

## 7. Phase 2 preview (NOT started — design with the owner first)

- Film domain model replacing books: Work/Edition/Author/Shelf → films (title, year, cast, crew, rating), watched-lists, reviews
- Metadata integration (TMDB is the leading candidate)
- Custom ReelTalk logo/artwork to replace the placeholder wyrm assets
- Domain + TLS deployment for a first public instance
- Crowdin re-sync of translations

## 8. Environment notes

- Session 1 machine: Fedora 44, x86_64, git 2.55, `gh` 2.97.0 in `~/.local/bin`, no Docker. The local clone at `/home/minnix/reeltalk` there is just the 2-file seed — do not build on that machine (owner wants it kept lightweight).
- Build server: unknown profile — check tooling first (§6.1).
- Owner's GitHub: `minnixtx`. Git identity used in session 1: `minnixtx` / `61262716+minnixtx@users.noreply.github.com` (set globally on the session-1 machine; set whatever is appropriate on the build server, ideally the same).

## 9. Ground rules

- Keep this repo's license/attribution intact at all times (§3)
- No force-push, no destructive git ops, no package installs system-wide, and no Phase 2 design decisions without explicit owner confirmation
- Report verification results faithfully — if a test fails or a step was skipped, say so
