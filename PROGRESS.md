# ReelTalk — Progress Tracker

**Last updated:** 2026-09-03
**Audience:** any new session picking up this project. Read this first, then `PLAN.md` (the historical Phase 1 execution plan) if you need the original reasoning.

---

## 1. What this project is

**ReelTalk** is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) (base commit `afd5ec305`) retooled as a federated (ActivityPub) social site for **film reviews**. The owner is a B-movie/cult-film enthusiast; the name is final.

- Fork repo: https://github.com/minnixtx/reeltalk (GitHub account `minnixtx`)
- **License:** Anti-Capitalist Software License v1.4 (© 2020 Mouse Reeve) — *not* AGPL. Hard rules:
  - `LICENSE.md` must stay **byte-identical** to upstream; never rename or edit it.
  - Attribution to BookWyrm / Mouse Reeve is never stripped; upstream references (`bookwyrm.social`, `github.com/bookwyrm-social/*`, `joinbookwyrm.com`) are intentional provenance links — do not "fix" them.
  - Any move toward commercial use must stop and be flagged to the owner (ACRL forbids it).

## 2. Current state (as of 2026-09-03)

| Area | State |
|---|---|
| Phase 1 (rebrand + deployment simplification) | ✅ Done, pushed, verified (full test suite green ×2) |
| Pre-Phase-2 changes (no HTTPS, no anubis, :3030 endpoint, no CONTRIBUTING) | ✅ Done, pushed (owner-directed, 2026-08-23) |
| CSRF trusted-origins fix | ✅ Done, pushed (2026-08-24) |
| Local instance | ✅ Running, **migrated to 0254** (2026-09-03): `initdb` seeded, admin account via `/setup` wizard (2 users), `install_mode=false`. Reachable at **http://192.168.1.138:3030**. DB contents (the 1,378-film TMDB watchlist import + backfill, 2026-09-02) are **disposable test data per owner confirmation 2026-09-03** — not precious production data; throwaway users created for verification are fine to hard-delete. Daily pg_dump backups land in the `backups` volume |
| Phase 2 — milestone 1 (UI rebrand books→films + binary film shelf model) | ✅ Done, committed, pushed, verified live (full test suite green: 1332 passed) |
| Phase 2 — milestone 2 (film domain model + AP rework) | ✅ **Done, live-verified, PUSHED 2026-08-30** — `08af0c971` (model/AP/migrations), `2726a1067` (app layer), `dfa704781` (4 conversion-artifact fixes) + `192ea709f` (test rework, new baseline 975 passed). Migrations 0247→0249 applied to the live DB; full click-through green (37/37). Fork main = `a00c7cd1e` |
| Phase 2 — milestone 3 (TMDB film importer) | ✅ **Done, live-verified, PUSHED 2026-08-31** — `e709614e2` (TMDB client), `e9bd0b007` (import page). Suite green: 998 passed. Fork main = `a0342a3c0`. Decisions #21–24 |
| Phase 2 — search UX rework (TMDB as primary catalog, "Watchlist" rename) | ✅ **Done, live-verified, pushed to fork 2026-09-01** after owner review (owner exercised the flow live; three follow-up issues reported — see §5 backlog). `c7c920737` (rename + migration 0250), `8832a5a8e` (TMDB global search + click-through + watchlist action), `710e18038` (import page removal). Suite green: 999 passed. Decision #25 |
| Phase 2 — owner-reported issues 2+3 (TMDB metadata lock, one review per film) | ✅ **Done, suite + live-verified, PUSHED to fork 2026-09-01** after owner review. `f98542481` (decision #26), `5acf6a3be` (decision #27). Suite green: **1017 passed / 1 skipped / 1 xfailed** |
| Phase 2 — owner-reported issue 1 (search-as-you-type dropdown) | ✅ **Done, suite + live-verified 2026-09-01, PUSHED to fork 2026-09-02** after owner review. `de929e896` (suggest endpoint), `6c7658b8c` (client dropdown), `2a112670f` + `607cad2fa` (test-env + poster-URL fixes). Suite green: **1029 passed / 1 skipped / 1 xfailed**. Owner then reported a poster-display bug → issue 4 |
| Phase 2 — owner-reported issue 4 (suggest-dropdown poster display) | ✅ **Done, suite + live-verified, PUSHED to fork 2026-09-02** after owner review. `5397f486a` (Bulma navbar img max-height clamp), `fb4cf48b7` (lazy loading in the scrollable menu). Suite green: **1029 passed / 1 skipped / 1 xfailed** |
| Phase 2 — file-based film import + export rework (decisions #29–31) | ✅ **Done, suite + live-verified 2026-09-02, PUSHED to fork 2026-09-03** — `aea3e497c` (import), `01e179539` (export to TMDB format). Live-verified with the owner's real 1,670-row TMDB watchlist export. Suite green: **1043 passed / 1 skipped / 1 xfailed** |
| Phase 2 — async TMDB backfill for imported films (decision #32) | ✅ **Done, suite + live-verified 2026-09-02, PUSHED to fork 2026-09-03** — `694c621eb`. Owner reported no posters/metadata on their imported films (a design gap in #29–31: the import makes no API calls and left ID stubs); a background task now fetches TMDB details + poster after each import. Live-verified: 1,372 of the owner's 1,378 stubs backfilled; the 6 remaining confirmed poster-less on TMDB. Suite green: **1050 passed / 1 skipped / 1 xfailed** |
| Phase 2 — housekeeping fixes (login 500 on missing field, nginx error caching) | ✅ Done 2026-09-02, PUSHED to fork 2026-09-03 — `0c840369d`, `802e3a658` (both live-verified) |
| Phase 2 — structural correctness audit + Quotation removal (decision #33) | ✅ **Done, suite + live-verified 2026-09-03, PUSHED to fork 2026-09-03** — `c22868337` (Quotation removed end-to-end), `1d857c0a5` (four flagged nits), `daa64522b` (shared_films annotation), `4c3554d2a`/`989f84cbe`/`331ad10ba`/`1bb4fdf40` (four live-verification bugs, incl. a cross-user shelf deletion that damaged one owner row — restored from pg_dump). Suite green: **1051 passed / 1 skipped / 1 xfailed**. Live stack rebuilt to 0253; owner data verified intact at baseline counts |
| Phase 2 — Crowdin/translation removal (decision #34) | ✅ **Done, suite + live-verified 2026-09-03, PUSHED to fork 2026-09-04** — `ba4b3cb18` (set_language removed), `ccd5747f2` (User.preferred_language + migration 0254), `110c47da1` (crowdin.yml + locale/ + settings i18n wiring). English-only for now; re-introduction = new Crowdin project + crowdin.yml + makemessages. Suite green: **1051 passed / 1 skipped / 1 xfailed** (baseline unchanged — no test touched translations). Live stack rebuilt to 0254 |
| Phase 2 — remainder after rework (artwork, public deploy) | ⬜ Not started (owner: design work happens with the owner, at the very end) |

## 3. Commit history (`main`)

```
110c47da1 Remove the Crowdin/translation component; pin English (decision 34)                ← decision #34 (commit 3/3: crowdin.yml + locale/ + settings i18n wiring)
ccd5747f2 Remove User.preferred_language (English-only, decision 34)                         ← decision #34 (commit 2/3: migration 0254 + form field + template control)
ba4b3cb18 Drop the set_language helper and its call sites (English-only, decision 34)        ← decision #34 (commit 1/3)
1bb4fdf40 Scope reading-status lookup to the requesting user (cross-user shelf deletion)      ← live audit bug 4/4 (owner row restored from dump)
331ad10ba Skip author header in compose view when there is no draft (500 on GET /post/<type>/)  ← live audit bug 3/4
989f84cbe Guard empty ids in get_mergeable_object_or_404 (absorbed lookup matched every row)   ← live audit bug 2/4
4c3554d2a Fix 0252 feed-filter data migration crash (queryset .update(), regression test)      ← live audit bug 1/4 (crashed the rebuild)
daa64522b Annotate suggested users with shared film counts (directory, feed, group surfaces)   ← shared_books dead-stat gap
1d857c0a5 Fix four flagged app nits from the milestone 2 sweep                                  ← six flagged nits (two died with Quotation)
c22868337 Remove the Quotation feature end-to-end (decision 33)                                 ← decision #33
3ca6248b8 Record push of file-based import, backfill, and housekeeping fixes to fork
42887fe1f Record async TMDB backfill for imported films (decision 32); note per-service image gotcha
694c621eb Backfill TMDB metadata + posters for imported films in the background (decision 32)  ← file-based import: poster/metadata gap
01e179539 Rework Export Film List to the canonical TMDB CSV format (decision 31)          ← file-based import (commit 2/2)
aea3e497c Add file-based film import from a TMDB-style CSV export (decision 29)           ← file-based import (commit 1/2)
802e3a658 Stop nginx from caching anonymous error responses                               ← housekeeping: cache poisoning fix
0c840369d Harden login form against a missing localname field                             ← housekeeping: login 500
b95efd658 Record issue 4 push; note login-form missing-field 500 as known item
d98904b53 Record issue 4 fix: dropdown poster display (max-height clamp + lazy loading)
fb4cf48b7 Drop lazy loading from suggest dropdown posters; unreliable in the scrollable menu
5397f486a Unclamp suggest dropdown posters from Bulma's navbar img max-height             ← owner-reported issue 4 (CSS)
b9108d869 Record issue 1 push; log dropdown poster-display bug as issue 4 for next session
4ffd8f878 Record issue 1 execution: search-as-you-type dropdown, awaiting owner review
607cad2fa Use relative media URLs for fallback suggest posters; works on any origin     ← owner-reported issue 1 (fix)
2a112670f Make poster URL assertion data-driven; media dir persists between test runs   ← owner-reported issue 1 (test env)
6c7658b8c Add search-as-you-type dropdown to the main search box (decision 28)          ← owner-reported issue 1 (client)
de929e896 Add JSON suggest endpoint for search-as-you-type (decision 28)                ← owner-reported issue 1 (endpoint)
45b8fd544 Record decision 28: search-as-you-type design aligned with owner
e625d8fe3 Record owner-reported issues 2+3 execution; propose issue 1 design
5acf6a3be Enforce one review per film; make rating-only entries editable (decision 27)  ← owner-reported issue 3
f98542481 Lock TMDB-sourced film details from user editing (decision 26)                ← owner-reported issue 2
111d9b830 Note that live DB contents are disposable test data (owner confirmed)
99ca8adc9 Update README status and roadmap to reflect Phase 2 progress
0498860c0 Remove repo-root CODE_OF_CONDUCT.md
095310d0d Record owner's scope answers: lock TMDB films only; live duplicate review cleaned up
d79e0104c Record owner review of search rework; queue three follow-up issues (decisions 26-27)
31728fbfc Record search UX rework execution: commits, new baseline, live verification
710e18038 Remove the TMDB import page                                                 ← search UX rework (commit 3/3)
8832a5a8e Query TMDB from global film search with one-click Watchlist add             ← search UX rework (commit 2/3)
c7c920737 Rename the Want to Watch shelf to Watchlist (display name only)             ← search UX rework (commit 1/3)
e9bd0b007 Add TMDB film import page: search, create-or-match, add to list or shelf   ← Phase 2 milestone 3 (commit 2/2)
e709614e2 Add TMDB API client for the film importer                                   ← Phase 2 milestone 3 (commit 1/2)
a00c7cd1e Mark Phase 2 milestone 2 as pushed in progress tracker
edffe01bd Record milestone 2 completion: test rework baseline, fixes, live verification
192ea709f Rework test suite onto the Film model; remove book-era tests                  ← Phase 2 milestone 2 (commit 3/3)
dfa704781 Fix four book-to-film conversion artifacts found by the test rework           ← Phase 2 milestone 2 (fixes)
b95617237 Update progress tracker with milestone 2 commit hashes
2726a1067 Rework views, templates and URLs onto the Film model; remove book-era features   ← Phase 2 milestone 2 (commit 2/3)
08af0c971 Replace book domain with flat Film model and federation wire types             ← Phase 2 milestone 2 (commit 1/3)
4203dc65f Mark Phase 2 milestone 1 as pushed in progress tracker
582f8138a Rework shelves into a binary film model; rebrand UI from books to films        ← Phase 2 milestone 1 (commit 2/2)
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

### Phase 2 — milestone 2 (executed 2026-08-25/26)

Owner design decisions for this milestone (see §8 #13–20): flat `Film` model, people as plain name fields, new `"Film"` AP wire type, data-migrate the local instance. During execution the owner added three more: **binary watch state only** (Want to Watch / Watched — no started/finished analogs), **silent watched** (marking a film watched posts *no* auto-generated note; sharing happens via reviews), and **watched requires a rating** (star rating out of 5 required, written review optional). Letterboxd is the loose design template for future design alignment (§8 #20).

**Commit 1/3 (`08af0c971`) — model + federation layer:**
- New flat `Film` model: title/sort_title/subtitle/description/year/runtime(int, minutes)/genres[]/directors[]/"cast"[] ArrayFields/poster (origin tmdb_id/imdb_id); `director_text` property. No shelves property (M2M reverse is `shelf_set`).
- **Book domain deleted:** Book/Edition/Work/Author/SeriesBook/ImportJob/ReadThrough/ProgressUpdate/FileLink/FindMissingCoversJob/SuggestionList(S) models + migrations 0247 (data: books→films, statuses/shelves/lists re-pointed) and 0248 (Connector + readwise removal).
- **Status MTI rework:** Comment/Review/Quotation are MTI children of Status via concrete `FilmStatus` base — each has its own `film` FK; `ReviewRating(Review)` for rating-only entries; PK is `status_ptr_id`.
- **New `"Film"` AP wire type** in `reeltalk/activitypub/`; book/author/note wire types removed.
- Historical migration fix: squashed 0006 imported the deleted `reeltalk.models.connector` (broke all migration loading) — the `ConnectorFiles` enum values were inlined as a literal list so the constraint stays byte-identical for fresh DBs.

**Commit 2/3 (`2726a1067`) — app layer:**
- **URLs:** `/book/<id>` → `/film/<id>` throughout; reading-status routes now `want|finish` only (`/reading-status/want/<film_id>/`, `/reading-status/finish/<film_id>/`); list item routes renamed (`list-add-film`, `list-remove-film`, `list-set-film-position`); block/unblock film routes named (`block-film`, `unblock-film`).
- **Binary watch state finished:** `ReadingStatusChoices` = to-read/read (migration 0249 AlterField on comment/quotation/review); `Shelf.READ_STATUS_IDENTIFIERS` = (to-read, read) — READING/STOPPED_READING constants kept only because migration 0146 imports them at runtime; status headers reduced to `wants to watch` + `finished watching` (+ review/comment/quotation/rating); `handle_reading_status` map now only `{"to-read": "wants to watch"}`.
- **Finish flow (owner decisions):** POST finish validates a rating (float 0.5–5, checked *before* any DB writes due to transaction commit semantics) → shelves film to read → delegates to `CreateStatus.as_view()` as `"review"` (content present) or `"rating"` (rating-only). No "Post to feed" checkbox — watched is silent; want flow posts a comment or a "wants to watch" GeneratedNote.
- **Removals:** Connector + Readwise (views/routes/forms/templates/`readwise_api_key`), user book-list import (`import`, `user-import`, `import-status` routes, `settings/imports/*` templates, IMPORT/USER_IMPORT notification types + item templates), suggestion lists (`user-suggestions` route + template, SuggestionList models gone in 0247), cover-maintenance admin (FindMissingCoversJob views/routes/template section — model deleted in 0247), custom-shelf-era reading modals/headers.
- **Template pass:** all film pages rewritten on the Film model (`film/*`, `search/film.html`, `shelf/*`, `lists/*` incl. new `suggestion_search.html`, `get_started/films.html`, `feed/suggested_films.html`, notifications items, discover cards renamed to `large-film`/`small-film`, about/landing superlatives via `get_film_superlatives`/`get_landing_films`, guided-tour fragments re-anchored to the new `tour-*-film*` element ids).
- **Verified in container:** `makemigrations --check` clean, `manage.py check` no issues, `collectstatic` OK, and a full parse of all 340 templates through Django's engine (catches syntax errors + missing includes). **Test suite NOT yet re-run — the tests are still book-based; that is commit 3.**

### Phase 2 — milestone 2 completion (executed 2026-08-27/29)

**Commit `dfa704781` — four conversion-artifact fixes found by the test rework** (each verified by its scoped tests; all would have broken live pages, not just tests):
- `activitystreams.py`: audience query had `mention_films__film` — `mention_films` is already an M2M to Film, so every feed render FieldError'd. Fixed to `mention_films`.
- `forms/links.py`: `LinkDomainForm` was lost when the book-era forms file was deleted wholesale; admin domain-rename POST 500'd. Restored (FileLinkForm correctly stayed gone), dropped a copy-pasted `EmailBlocklistForm` from the link-domains GET context, added a regression test.
- `views/notifications.py`: `select_related("related_import")` referenced an FK removed with the import feature — notifications page 500'd for all users. Now `related_user_export`.
- `templates/lists/item_notes_field.html`: closing `</div>` dropped in the string pass — list pages with editable notes failed tidy validation (found via div-depth tracing of the rendered page).

**Commit `192ea709f` — test rework to green** (157 files, +2285/−16710):
- Deleted tests for removed features: connectors, importers, book views, user book-list imports, readwise, ISNI/ISBN, suggestion lists, series, cover jobs; 37 orphaned fixtures in `tests/data/`.
- Rewrote the rest against Film/ReviewRating/binary shelves: new model + AP wire `test_film.py`, films-stream tests, film display tags/search tests, film-era inbox payloads (inline AP JSON with `inReplyToFilm` and literal origin ids — `Film.save()` nulls `remote_id` on new rows), initdb `edit_film` codename, finish-flow rating requirement.
- **New green baseline: 975 passed / 1 skipped / 1 xfailed / 52 subtests** (was 1332 pre-milestone-2; the delta is removed-feature coverage). Run twice, CI-faithful flow.

**Live verification (2026-08-29):**
- `docker compose up -d --build` + nginx restart: **migrations 0247/0248/0249 applied to the live DB cleanly** (it had zero book rows, so 0247's data conversion was a no-op; daily pg_dump backups exist pre-migration in the `backups` volume).
- Permissions: entrypoint's `initdb` auto-created `edit_film` and granted it to all four groups. Manually cleaned **23 stale content types + 92 permissions** for removed models (Django never deletes stale content types on migrate) plus the orphaned custom `edit_book` permission — 0 dangling perms remain.
- **Click-through: 37/37 green** with a throwaway user (hard-deleted afterwards; live DB back to its original 2 users / 0 films): login, feed, create film, film page (301 slug redirect works), Want to Watch shelve + note, finish-without-rating rejected pre-DB-write ("A star rating is required"), rating-only finish → silent `ReviewRating` + Watched shelf, written-review finish → `Review`, list create/add×2/reposition/remove, search finds both films, block/unblock film (blocked hidden from search), admin files-maintenance page renders.

**Flagged app nits found by the rework (NOT fixed — owner's call):**
- `Film.viewer_aware_objects()` returns a raw Manager for anonymous viewers (all current call sites chain `.filter()`, so no live breakage).
- `Status.delete()` soft-delete clears a nonexistent `quotation` attr (the field is `quote`) — soft-deleted quotations keep their quote text.
- `Quotation.pure_content`: first regex line is dead code — opening quote mark missing on plain-text quotes in cross-instance display.
- `ShelfFilm.save()`: `if not self.user:` raises on an unsaved instance with no user (all view call sites pass `user`; migration 0247 uses schema-level renames, so latent only).
- `templatetags/rating_tags.py::get_rating` counts soft-deleted reviews in a film's average while `get_user_rating` excludes them.
- `settings/link_domains/link_domains.html` still says "shown on book pages" (string-pass leftover).

### Phase 2 — milestone 3 (executed 2026-08-30/31)

Owner design decisions for this milestone (see §8 #21–24): **TMDB** API; key via `REELTALK_TMDB_API_KEY` in `.env` (operator-set, all users may import; unset → not-configured notice); dedup = exact ID match + **title/year fallback** that backfills `tmdb_id` and empty metadata onto manually created films; scope = core flow with destination = any of the user's lists **or the Want to Watch shelf** (bulk import out).

Note: the §5 note "UI chrome partly exists already" was stale — milestone 2 removed the import routes/templates entirely, so this milestone builds its own page.

**Commit 1/2 (`e709614e2`) — TMDB client:**
- `reeltalk/tmdb.py`: v3 REST client — `search/movie`, `movie/{id}` with `credits,images` appended, poster download from the image CDN; `TmdbError` for user-facing failures (invalid key 401, rate limit 429, network); `film_fields_from_tmdb()` maps a details payload onto Film fields (cast capped at 10).
- `settings.TMDB_API_KEY` from the optional `REELTALK_TMDB_API_KEY` env var; documented in `.env.example`.

**Commit 2/2 (`e9bd0b007`) — import page:**
- `/import/` (route `import-films`), reachable from the preferences sidebar ("Import Films" under Data) and each list page ("Or search TMDB for films to import", target preselected).
- Flow: pick destination (own lists + group-member lists, or Want to Watch shelf for local users) → search TMDB → results grid with posters; hits already in the library get an "In your library" badge and link to the film page → per-row "Add to <destination>" button.
- Create-or-match: exact `tmdb_id` match via `Film.find_existing()`; else title+year fallback (normalized sort_title + year) that backfills `tmdb_id` + empty fields onto the manual film; else creates a new Film with full TMDB metadata + poster.
- Add: lists reuse ordering logic extracted from the list-add view (`set_list_item_order`, so curated-list pending state behaves identically); shelves create a ShelfFilm on Want to Watch (Watched is not a destination — decision #19). Duplicates rejected with a message; after adding, the results grid re-renders and the added row is marked.
- **New green baseline: 998 passed / 1 skipped / 1 xfailed / 52 subtests** (was 975; +23 new tests: 10 client + 13 view).

### Phase 2 — search UX rework (executed 2026-08-31, awaiting owner review)

Owner redirect after reviewing milestone 3 (decision #25): TMDB becomes the **primary film catalog** reached from the main search box (Letterboxd model), with one-click "Add to Watchlist" and click-through to film pages; "Want to Watch" is renamed to "Watchlist" everywhere (display name only); the `/import/` page is removed ("Import" reserved for future file-based imports). The create-or-match/backfill mechanics from m3 survive in the search flow.

**Commit 1/3 (`c7c920737`) — Watchlist rename:**
- `create_shelves` default name → "Watchlist"; **data migration 0250** renames existing `to-read` shelves ("Want to Watch" → "Watchlist"). The identifier stays `to-read` — it's wire format, unchanged.
- Display strings updated: profile header (`user/user.html`), shelf page title, shelf selector, both shelve-button variants, get-started film picker. Status phrases ("wants to watch") and sentence copy ("Want to watch 'X'?") intentionally untouched.

**Commit 2/3 (`8832a5a8e`) — TMDB global search:**
- `film_search()` in `views/search.py` queries TMDB when `REELTALK_TMDB_API_KEY` is set; falls back to the local trigram search when unset (graceful degradation per #22). User/list search and the federated API endpoint (`api_film_search`) are unchanged — the API stays local-only.
- Result rows: CDN poster + title + year. Local matches link straight to the film page with an "In your library" tag; unmatched hits link to a new click-through route `GET /search/film/<tmdb_id>/` that runs create-or-match (exact `tmdb_id` → normalized title+year backfill → create with full metadata + poster) and redirects to the film page.
- One-click "Add to Watchlist" per row: `POST /search/film/<tmdb_id>/watchlist/` (login required, local users only; a hidden `return_to` field preserves the results grid). Create-or-match + shelve onto the `to-read` shelf, then redirect back; the row re-renders with an "On your watchlist" state. Anonymous users see results without the action; locally blocked films are excluded from TMDB results (with the usual notice).
- `tmdb.search_films()` now returns page metadata (`total_results`/`total_pages`) and passes `page` through to the API; a small `TmdbPaginator` feeds the standard pagination markup.
- Reusable helpers moved from `views/import_films.py` into `reeltalk/tmdb.py`: `find_local_film`, `ensure_local_film` (now also handles missing title/year by fetching details once), `backfill_film_from_tmdb`, `add_poster`.

**Commit 3/3 (`710e18038`) — import page removal:**
- Removed the `/import/` URL, view module, template and tests; removed both entry points (preferences sidebar "Import Films", list-page "Or search TMDB…"). `set_list_item_order` in `views/list/list.py` stays — `add_film` uses it.

**New green baseline: 999 passed / 1 skipped / 1 xfailed** (was 998; −13 import-page tests, +14 TMDB search tests). The local-fallback search tests pin `TMDB_API_KEY=''` via `override_settings` so the suite is deterministic on hosts where the live `.env` sets a real key (see §7 quirk 5).

**Live verification at :3030 (2026-08-31), throwaway user:** rebuild applied **migration 0250 cleanly** (both existing users' `to-read` shelves renamed, identifiers unchanged); new-user creation gets a "Watchlist" shelf. **15/15 click-through checks green:** anonymous search renders TMDB results with posters and no add button; logged-in rows carry "Add to Watchlist"; one-click POST → redirect back to the grid → "On your watchlist" state on that row; click-through on an unmatched hit created the local film (full metadata + poster) and opened its page, which shows the Watchlist action and "View on TMDB"; profile header and shelf page show "Watchlist"; `/import/` 404s. Throwaway user hard-deleted afterwards — live DB back to its original state (2 users / 0 films).

**Pushed to fork main on 2026-09-01** after owner review — including `baaa8f2bd` (the plan commit) that was sitting unpushed locally; fast-forward, no force. Owner exercised the flow live afterwards and reported three follow-up issues (search-as-you-type dropdown, TMDB metadata editability, duplicate reviews) — captured in §5 as the next session's backlog (decisions #26–#27).

### Phase 2 — owner-reported issues 2+3 (executed 2026-09-01, awaiting owner review)

The two settled issues from the owner's live use of the search rework (decision log #26–#27), in the suggested order. Issue 1 (search-as-you-type) is **not** started — it needs design alignment first (§5).

**Commit `f98542481` — TMDB metadata lock (decision #26):**
- Films with a `tmdb_id` are locked in the UI: the edit pencil, the "Add Description" block and the poster-upload control are hidden on the film page; `EditFilm` GET/POST, `upload_poster` and `add_description` redirect without saving. Manually created films (no `tmdb_id`) stay fully editable — scope confirmed by the owner.
- New test file `tests/views/test_films.py` (first coverage of the film page + edit views). It surfaced two latent template bugs, fixed in-line: the add-description `<textarea>` rendered literal `rows="None" cols="None"`, and unescaped `&` in the create-status tab hrefs (tidy failures — the film page had never been rendered logged-in-with-edit-perms in the suite before).
- Inbound federation updates to TMDB films are untouched (the decision is about the user-facing UI).

**Commit `5acf6a3be` — one review per film (decision #27):**
- **UI:** wherever the Review tab was offered (`snippets/create_status.html` — film page, Home "Your Films" panel, compose), a user who already has a review for that film gets an **"Edit review"** link instead; the review panel shows a notice + edit link. Comment/Quote tabs are unchanged (transient, multiple allowed). New `get_user_review` template tag (status_display) does one query per film.
- **Guard:** `CreateStatus.post` rejects a *new* review when the user already has one for that film (web → redirect back, API → 400). "Already reviewed" = any `Review` instance, **including rating-only `ReviewRating` entries** — they are the user's review of the film in this data model.
- **Finish flow:** finishing a film that already has a review now *updates* that review instead of creating a second entry (the submitted rating is applied; an empty modal text keeps the review's current content, re-fed through the markdown pipeline via `raw_content`). This closes the remaining duplicate path: written review first, then "Mark as watched" with a rating.
- **Rating-only entries became editable** (they previously had no edit path at all — `raise_not_editable` blocked them, there was no `rating.html` create template, and the status dropdown hid Edit for `Rating` type): `EditStatus` renders them as a review edit ("Edit review" heading), the dropdown offers Edit again, `ReviewForm` requires the rating to stay set when editing one (clearing it is a form error, not a save-time crash), and a rating entry that gains content shows its stars header (`show_review_header` tag — Django template `{% if %}` can't group with parentheses).
- **Test-environment fix:** two upload-URL assertions in `test_status.py` were made data-driven. The `media_volume` named volume persists between test runs, so Django suffixes version filenames on re-save (`240.jpg` → `240_MuQ6bzv.jpg`) and exact-path expectations break — see §7 quirk 6.
- New tests: duplicate-review rejection (web + API), rating-entry edit panel/update/clear-rejected, finish-updates-existing-review (content kept / replaced), film-page edit-only vs new-reviewer markup.

**Verification:** full CI-faithful suite green — **1017 passed / 1 skipped / 1 xfailed** (baseline 999 + 18 new). Live click-through at :3030 as the owner account: 20/20 checks green — TMDB film (*Camp Hideaway Massacre*) page has no edit controls, `/film/<id>/edit/` redirects, poster/description POSTs rejected with metadata intact; a manually created film kept all editing affordances and saved an edit; reviewed films show "Edit your review" on the film page **and** in the Your Films panel with no new-review form; duplicate review POST rejected (owner's review id 8 untouched); rating-only finish → entry editable in place (rating 4→4.5 + content added, cleared-rating rejected); finish on a reviewed film produced exactly one updated status (rating applied, text preserved). All disposable films/statuses hard-deleted afterwards — live DB back to its original state (2 users, films 16/17, reviews 8/10).

### Phase 2 — owner-reported issue 1: search-as-you-type dropdown (executed 2026-09-01, awaiting owner review)

Executed per the agreed spec in §5 (decision #28). Four commits:

**Commit `de929e896` — suggest endpoint:**
- `GET /search/suggest/?q=<term>&type=film` → JSON `{"results": [{title, year, poster, url}]}`. Local users only: anonymous **and federated** users get an empty list (and no TMDB call); queries under 2 chars and non-film types return empty without calling out.
- With `REELTALK_TMDB_API_KEY` set: `tmdb.search_films()` page 1, top 8 rows. Each row is annotated with its local match (`tmdb.find_local_film`) — a match links straight to the film page, an unmatched hit links to the existing click-through route `/search/film/<tmdb_id>/`. Locally blocked films are dropped from the rows (consistent with the full TMDB search). A `TmdbError` degrades to no suggestions rather than an error.
- Without the key: local trigram fallback (`book_search.search`, min_confidence 0.1), top 8, blocked films excluded, nothing when there are zero matches.
- `CSP_IMG_SRC = ['self', https://image.tmdb.org]` added globally in settings — the dropdown shows TMDB CDN posters from the navbar on **every** page, but the default CSP only allowed `'self'` (the Search view's per-page `IMG_SRC="*"` didn't cover the rest of the site).
- 12 new tests in `tests/views/test_search.py::FilmSuggestViews`.

**Commit `6c7658b8c` — client dropdown:**
- New vanilla-JS file `static/js/search_suggest.js` (IIFE, no dependencies): binds to the navbar input `#tour-search`, ~300 ms debounce, min 2 chars, renders rows (poster + title + year) into a dropdown under the input; **click-only** — clicking a row navigates (local match → film page; TMDB-only hit → click-through route); Enter still submits the normal search form. Closes on outside mousedown / new results / submit. Rows without a poster get a CSS no-cover placeholder (no static-image URL in JS — manifest storage hashes filenames).
- `layout.html`: dropdown div + script include, both gated `{% if request.user.is_authenticated and request.user.local %}` — anonymous/remote users get no dropdown DOM at all. New SCSS component `_search_suggest.scss` (imported in `_all.scss`).

**Commits `2a112670f` + `607cad2fa` — fixes found during verification:**
- `test_film.py::test_serialize_model_with_poster` asserted the exact upload path `posters/test-poster.jpg`; when the media directory persists between runs (quirk 6, via the bind-mounted `images/` in the CI-faithful flow) Django suffixes the re-saved filename and the second run fails. Made data-driven (`endswith(film.poster.name)`), same rule as the `test_status.py` fix.
- Fallback-mode posters were returned as `{MEDIA_FULL_URL}…` — with `DOMAIN=localhost` that's `http://localhost:80/images/…`, a broken absolute URL for browsers reaching the instance on :3030/LAN. Now `film.poster.url` (relative, like the rest of the UI); regression test added.

**Verification:** full CI-faithful suite green **twice in a row** — **1029 passed / 1 skipped / 1 xfailed** (baseline 1017 + 12 suggest tests + 1 poster-URL regression). Live click-through at :3030 with a throwaway local user (hard-deleted afterwards; live DB back to 2 users, films 16/17):
- **TMDB mode (live key):** anonymous `/search/suggest/` → `{"results": []}`; logged-in "blade runner" → 8 rows, local *Blade Runner* (film 17) linked to its film page, unmatched hits linked to `/search/film/<tmdb_id>/`; click-through on *Blade Runner 2049* (335984) created the local film (full metadata + poster, no duplicate on re-click) and opened its page; dropdown markup + hashed `search_suggest.*.js` present for the logged-in local user, absent for anonymous; CSP header carries `img-src 'self' https://image.tmdb.org`.
- **No-key mode** (throwaway web container with `REELTALK_TMDB_API_KEY=` unset on :3031, same DB): "blade" → local trigram matches only, posters as relative `/images/…` URLs; zero-match query → empty list.

**Testing gotcha found (for future sessions):** asserting "no HTTP call was made" via `responses.RequestsMock()` + `rsps.calls == []` proved flaky under pytest-xdist (a call from elsewhere in the worker process occasionally lands in the fresh mock's CallList; 4/4 → 3/4 → 0/4 across runs, never reproducible in-process or in later xdist runs). The deterministic replacement — `patch("reeltalk.views.search.tmdb.search_films")` + `assert_not_called()` — is what the no-call tests use now.

### Phase 2 — owner-reported issue 4: suggest-dropdown poster display (executed 2026-09-02, awaiting owner review)

Fixed per the §5 bug report. Two distinct root causes behind the two symptoms; CSS/JS only, no endpoint change, no test changes (no test touches these files). Reproduced in headless Chromium against the exact served assets before touching anything (harness: real compiled theme CSS + real `search_suggest.*.js` + real `/search/suggest/?q=blad` payload; computed-style logging via console → stderr).

**Commit `5397f486a` — posters filled only the top ~55–60% of their cell, `$no-cover-color` band below:**
- Root cause: Bulma's stock `.navbar-item img { max-height: $navbar-item-img-max-height }` (1.75rem = 28px) exists to cap the navbar **logo**, but the search *form* is itself a `.navbar-item` (`layout.html`), so the rule also matched every dropdown poster `img`. The component rule set `height: 100%` but nothing reset `max-height`, so posters were clamped to 28px inside their 54px cells (repro: span computed 36×54, img computed 36×28).
- Fix: `max-height: none` on `.search-suggest-poster img` (`_search_suggest.scss`). Same specificity as the Bulma rule and later in source order, so it wins; scoped to the component, so the logo cap is untouched (logo still renders under the theme's own `.navbar .logo { max-height: 50px }` override).

**Commit `fb4cf48b7` — some queries showed no posters at all:**
- Root cause: `img.loading = "lazy"` inside the absolute-positioned `max-height:420px; overflow-y:auto` menu. Real-time headless-Chromium repro with 8 poster rows: only the first ~5 loaded and the rest never did — including one row *inside* the menu's scroll area (known Chromium flakiness for lazy images in small scrollable containers).
- Fix: dropped `loading="lazy"` in `search_suggest.js` (rows are capped at 8, so eager load is cheap); kept `decoding="async"`.

**Verification:** CI-faithful suite green — **1029 passed / 1 skipped / 1 xfailed** (baseline unchanged). Live re-check at :3030 on a real logged-in session driven over CDP (query "blad", TMDB mode):
- All 5 poster rows: img box = cell box (36×54), computed `max-height:none; object-fit:cover`, all images loaded — including the below-the-fold row that lazy loading had been deferring.
- All 3 no-poster rows: flat `$no-cover-color` cells, unchanged.
- Navbar logo unaffected (still capped by the theme's 50px rule).

### Phase 2 — housekeeping fixes: login 500 on missing field + nginx error caching (executed 2026-09-02, PUSHED to fork 2026-09-03)

Two observations from this session's live probing; both fixed with the narrowest change that works.

**Commit `0c840369d` — login POST 500 when the `localname` field is missing:**
- Root cause: `LoginForm.infer_username` did `"@" in self.data.get("localname")` — a `TypeError` on `None`. Any POST that omits the field entirely (malformed clients; browsers always send it) 500'd before form validation could run. Covers both call sites (`Login.post` and `ReactivateUser.post`).
- Fix: one line — `localname = self.data.get("localname") or ""`, so a missing field behaves like an empty one and the request falls through to the usual generic invalid-credentials response.
- Regression test: `tests/views/landing/test_login.py::test_login_post_missing_localname` (POST with only `password` → 200 + "Username or password are incorrect").

**Commit `802e3a658` — nginx caching anonymous error responses:**
- Root cause: this session's first live probe hit `127.0.0.1`, which is not in `ALLOWED_HOSTS` → Django DisallowedHost 400. Nginx's `proxy_cache_valid any 1m` plus a cache key that ignores the client's `Host` header stored that 400 and served it to `localhost` requests for up to a minute — a transient error on one host poisoned every other host.
- Fix: `proxy_cache_valid 200 1m;` in `nginx/locations` (only successful responses are cached). The config is bind-mounted, so `docker compose restart nginx` was enough — no rebuild.

**Verification:** scoped tests green (`tests/views/landing/test_login.py`, 10 passed); the full-suite run below includes both fixes. Live at :3030: login POST with a missing `localname` → 200 + generic error (no more 500); a DisallowedHost probe on `127.0.0.1` no longer poisons subsequent `localhost` requests, and the normal cache path is intact (MISS→HIT).

### Phase 2 — file-based film import + export rework (decisions #29–31; executed 2026-09-02, PUSHED to fork 2026-09-03)

Design settled with the owner first (§8, decisions #29–31): **TMDB-style CSVs only** — the canonical ten-column header is TMDB's own export shape (the owner's watchlist export is the reference), and ReelTalk's "Export Film List" now emits the same format so exports round-trip. No TMDB API calls during import; a synchronous single-page flow with a per-row results table + summary.

**Commit `aea3e497c` — Import Film List (`/preferences/import/`, Preferences → Data):**
- New view `reeltalk/views/preferences/import_films.py`: header validation against the canonical ten columns ("Not a recognized TMDB export — missing column(s): …"), 20,000-row cap, `utf-8-sig` decode (TMDB exports carry a BOM), the whole import in one transaction.
- Per row: **create-or-match** — TMDb ID first, then IMDb ID (`Film.find_existing`), then normalized sort-title + year; on match, empty local `tmdb_id`/`imdb_id`/`year` are backfilled from the row. Non-movie rows (`Type` ≠ movie) and missing-name rows are skipped with a note.
- **Rating mapping (decision #30):** TMDB's 1–10 `Your Rating` is mapped ÷2 onto ReelTalk's 5-star scale (nearest half star). Unrated row → film added to Watchlist; rated row → film shelved as Watched + a `ReviewRating` at the mapped value. Existing reviews are never touched (decision #27). All saves use `broadcast=False` — importing your own data is not federation.
- UI: `templates/preferences/import_films.html` — file picker, then a per-row results table (line number / name / status / note) + summary counts; "Import Film List" link added to the Data section of the preferences layout, above Export.
- 13 new tests in `tests/views/preferences/test_import_films.py` (header rejection, row cap, create+watchlist, rating mapping, ID match + backfill, title+year match, TV skip, missing-name skip, watchlist no-op, existing-review untouched, summary counts/line numbers).

**Commit `01e179539` — Export Film List reworked to the canonical TMDB CSV (decision #31):**
- `Export.post` now writes the same ten-column header (`tmdb.TMDB_EXPORT_HEADER`, a shared constant in `reeltalk/tmdb.py`) with one row per film the user has a relationship with (shelved / reviewed / commented / quoted): TMDb + IMDb IDs from the film, `Type` = "movie", Release Date = stored year as `YYYY-01-01T00:00:00Z`, Your Rating = most recent rated review ×2, Date Rated from that review's published date (UTC); season/episode and community-score columns empty. Review text drops out by design — the format carries ratings, not reviews.
- `templates/preferences/export.html` copy rewritten (was book-era "Export Book List"/Goodreads); the form tag was also fixed (`action=`, was an invalid `href=`).
- `tests/views/preferences/test_export.py` rewritten in place: header equality + row values + rating/date mapping (4 tests).

**Verification:** full CI-faithful suite green — **1043 passed / 1 skipped / 1 xfailed** (baseline 1029 + 1 login regression + 13 import tests; export tests rewritten in place, net zero). Live at :3030 with the owner's real 1,670-row TMDB watchlist export:
- Import as a throwaway local user: **1,378 films created → Watchlist**, 292 rows skipped ("not a movie (tv)" — by design), 0 matched. The zero is correct: none of the three pre-existing films (16 *Camp Hideaway Massacre*, tmdb 516695; 17 *Blade Runner*, tmdb 78; 22 *The Wolverine: Path of a Ronin*, tmdb 447158) appear in the file. Film count reconciles exactly (3 + 1,378 = 1,381).
- Export round-trip is byte-exact for an unrated film (e.g. `102938,tt0075344,movie,Trackdown,1976-01-01T00:00:00Z,,,,,`); re-importing that export is a pure no-op (all 1,378 matched, nothing created).
- A film page renders correctly (year + "View on TMDB" link); celery worker logs clean.
- Cleanup: throwaway user hard-deleted in PROTECT order (ShelfFilm → Shelf → Films → User); live DB back to its original state (2 users, films 16/17/22).

### Phase 2 — async TMDB backfill for imported films (decision #32; executed 2026-09-02, PUSHED to fork 2026-09-03)

After importing their own watchlist into the live instance, the owner reported that every imported film showed only a blue placeholder box — no poster on the watchlist or the film page. Investigation: the imports were ID stubs (title/year/TMDb+IMDb IDs only — no description, directors, genres, runtime, cast either). That is by design per decision #30 (no API calls during import), but there was no path to fill the data afterwards. Design aligned with the owner (decision #32): **async backfill after import** — a background job fetches TMDB details + poster for every imported film so the list looks complete without any user action (Letterboxd model: every film has its poster immediately).

**Commit `694c621eb`:**
- New Celery task `backfill_imported_films_task` (`reeltalk/tmdb.py`, `imports` queue): walks the given film IDs; skips films without a `tmdb_id` and films that already have a poster + description (idempotent — safe to re-queue); fetches details via `get_film_details()` and fills all empty fields via `backfill_film_from_tmdb()` + `add_poster()`. 0.25 s spacing between fetches keeps a large import under TMDB's 50-requests-per-10-seconds rate limit (1,378 films ≈ 15 min). A per-film `TmdbError` is logged and skipped — one failure never stops the batch; no-op when the instance has no API key.
- Import view: after the transaction commits (`transaction.on_commit`), queues every non-skipped film — created **and** matched, so re-importing a previously imported list backfills any stubs it left behind. Only when TMDB is configured; in that case the results page shows a note that posters/details are being fetched in the background.
- 7 new tests (5 task: unconfigured no-op, skip complete films, skip non-TMDB films, fill stub fields + poster, continue past per-film errors; 2 view: queue after commit with the right IDs, no queue when unconfigured).

**Verification:** full CI-faithful suite green — **1050 passed / 1 skipped / 1 xfailed** (baseline 1043 + 7). Live at :3030: rebuilt web **and** the celery worker/beat onto the new image (the worker's per-service image is separate — an un-rebuilt worker silently drops the new task as "unregistered"), then queued a one-off backfill of the owner's existing 1,378 stubs. Task succeeded in 925 s, zero failures: 1,372 films now have poster + description + directors (sampled rows verified); the 6 remaining were confirmed genuinely poster-less on TMDB (`poster_path: None` for all six — obscure titles). A film page renders with its poster (`/images/posters/tmdb-*.jpg`, 200 image/jpeg).

### Phase 2 — structural correctness audit + Quotation removal (decision #33; executed 2026-09-03, awaiting owner review)

Owner redirect after the backfill milestone: *"The artwork and design choices I want to leave until the very end. I first want to make sure that structurally everything works as it should so I will let you pick what we should focus on to achieve that goal."* Focus chosen: structural correctness — fix the six flagged app nits from the milestone-2 sweep, close the `shared_books` dead-stat gap, settle the Quotation question (decision #33), then verify live at :3030. Constraint for the whole session: **the live DB now holds the owner's real data** (their 1,378-film TMDB watchlist import + backfill) — never wipe or mangle it; throwaway users are fine to hard-delete.

**Commit `c22868337` — Quotation removed end-to-end (decision #33):**
- Clarified with the owner first: "quotation" is the book-era feature of quoting a line *from* a book — not one user quoting another in a reply. The owner confirmed film users won't add quotes from films (only reviews and star ratings) → remove entirely.
- Removed (47 files, +103/−516): `Quotation` model + MTI table (**migration 0251**), the `"Quotation"` AP wire type, the Quotation form + create/edit views/routes/templates (incl. the Quote tab in the create-status dropdown), quotation branches in notification item templates, the quotes RSS feed (`/user/<u>/rss-quotes/`), discover/feed/hashtag/user-page quotation handling, export of quotations, and all remaining "quotation" strings/tests.
- **Migration 0252 (data):** strips `"quotation"` from every user's `feed_status_types`; **migration 0253:** drops the choice from the field definition (choices are now review/comment/everything).
- Inbound federation: remote Quotation activities are gracefully skipped via the `naive_parse` ignore list — a remote instance quoting will not crash or create content here.
- Two of the six flagged nits died with this feature (`Status.delete()` clearing a nonexistent `quotation` attr; `Quotation.pure_content` dead regex).

**Commit `1d857c0a5` — the four remaining flagged nits:**
- `Film.viewer_aware_objects()`: anonymous viewers now get an empty queryset instead of a raw Manager (consistent with authenticated users; all call sites chain `.filter()`).
- `ShelfFilm.save()`: the missing-user guard no longer raises on an unsaved instance without a user.
- `rating_tags.get_rating`: now excludes soft-deleted reviews from a film's average, matching `get_user_rating`.
- `settings/link_domains/link_domains.html`: "shown on book pages" → films wording (string-pass leftover).

**Commit `daa64522b` — shared film counts (the `shared_books` gap):**
- `user.shared_books` was referenced by the directory user card + suggested-users snippets but no longer existed on User, so those "N films you share" stats silently didn't render. `suggested_users.py` now annotates both `get_annotated_users()` (directory) and `get_suggestions()` (feed / get-started / group surfaces) with a `shared_films` count — films on both users' shelves — and the three templates use it.

**Live verification at :3030 found four real bugs the 1,050-test suite could not** (all live-data-shape-dependent; each fixed + regression-tested):
1. **Migration 0252 crashed the live rebuild** (`4c3554d2a`): it called `user.save(broadcast=False)` — but RunPython migrations get *bare historical models* with no AP-mixin save override, so the kwarg is rejected; the suite never ran the loop body (no test user had "quotation" in their filter). Rewrote both directions with queryset `.update()` (no signals, no broadcasts) + new `tests/test_migrations.py` covering strip/restore.
2. **GET `/post/<type>/` without a film → 500** (`989f84cbe`): `get_mergeable_object_or_404(klass, id=None)` compiled the absorbed fallback to `WHERE deleted_id IS NULL`, matching every row → `MultipleObjectsReturned`. Empty ids now raise Http404 early.
3. **GET `/post/review/?film=<id>` → 500** (`331ad10ba`): compose.html included the status header with `status=draft` even when `draft` was undefined (Django passes `""` for undefined vars), crashing `get_header_template`'s attribute lookups. Header now skipped when there is no draft.
4. **Cross-user shelf deletion — data damage** (`1bb4fdf40`): `ReadingStatus.post` looked up `film.shelffilm_set` unscoped by user, so the audit's "want" POST deleted the **owner's** Watched ShelfFilm for film 16 (row id 22). Detected via the ShelfFilm count (1379 vs baseline 1380) + a pg_dump pair diff; the exact row was restored from the pre-rebuild dump (original id/timestamps/remote_id), and the lookup is now scoped to `request.user`. Verified live with a second throwaway user — the owner's row survived.

**Verification:** full CI-faithful suite green — **1051 passed / 1 skipped / 1 xfailed** (was 1050: Quotation-removal test deletions largely offset by the new regression tests). Live at :3030: full rebuild applied **migrations 0251–0253**; stale Quotation content type + permissions manually cleaned (Django never deletes them on migrate); AP probes green (nodeinfo, webfinger, Person + Film docs all 200); removed routes clean 404 (`/film/<id>/quote`, `/user/<u>/rss-quotes/`); **final click-through audit 34/34** as a throwaway local user — decisions #19 (rating required), #26 (TMDB films locked from editing), #27 (one review per film, incl. in-place update via the finish modal), #30–31 (export round-trip: CSV header + Your Rating mapping) and the async user-export tar job all hold live. Throwaway users hard-deleted; owner data verified intact at baseline counts (User 2 / Film 1,381 / Status 4 / Review 2 / Shelf 4 / ShelfFilm 1,380); fresh full pg_dump taken in the `backups` volume.

### Phase 2 — Crowdin/translation removal (decision #34; executed 2026-09-03, PUSHED to fork 2026-09-04)

Owner directive: ReelTalk is **English-only for now**; translations may be re-added later via volunteers, so the removal must be clean and re-introduction easy ("re-adding = new Crowdin project + crowdin.yml + makemessages"). Owner supplied a verified scope; one judgment call delegated (USE_I18N — kept True, see below). All `{% trans %}`/`gettext()` markers are **kept on purpose**: without catalogs they render as plain English no-ops, and stripping them would be a huge churn diff that makes re-adding translations harder.

**Commit 1/3 (`ba4b3cb18`) — set_language removed:**
- `set_language()` deleted from `views/helpers.py` (plus its now-unused imports: `translation`, `django.conf settings`, `timedelta`). Its five call sites became plain redirects: login (3 — first-login → get-started-profile, 2FA-prompt, final `/`), `LoginWith2FA.post` after code verification (`/`), and profile save (user page).

**Commit 2/3 (`ccd5747f2`) — User.preferred_language removed:**
- **Migration 0254** drops the column (hand-written; verified equivalent to Django's own diff via `makemigrations --check`). Historical migrations 0106–0195 that reference the field are untouched.
- Field removed from the User model (+ the `LANGUAGES` import), from `EditUserForm.Meta.fields`, and the "Language:" control from `/preferences/profile/`.

**Commit 3/3 (`110c47da1`) — Crowdin + locale + i18n wiring:**
- Deleted `crowdin.yml` and the entire `locale/` tree (49 BookWyrm-era catalogs, all carrying X-Crowdin headers pointing at the bookwyrm-social/bookwyrm project 479239), plus the Dockerfile's `COPY locale /app/locale`.
- settings: removed `LOCALE_PATHS`, `LANGUAGE_COOKIE_NAME`, `LocaleMiddleware`, and the 22-entry `LANGUAGES` list; **pinned `LANGUAGE_CODE = "en-us"`** (env override dropped); dead `LANGUAGE_CODE` test-env entries removed from pytest.ini + pyproject.toml.
- **Kept on purpose:** all `{% trans %}`/gettext markers; `USE_I18N = True` (L10N date/number formatting unchanged since Django 4 decoupled it — flipping to False would be a behavior change for zero benefit, and re-enabling is config-only either way); `LANGUAGE_ARTICLES` (domain data for film sort titles, not i18n machinery); nodeinfo's `"languages": ["en"]` (wire format); the gettext apt deps in the Dockerfile and the `rt-dev makemessages/compilemessages/update_locales` subcommands — they are the re-add toolchain.

**Re-introduction path (future session):** new Crowdin project for ReelTalk → fresh `locale/en_US/LC_MESSAGES/django.po` via `rt-dev makemessages` + a `crowdin.yml` pointing at it → restore `LOCALE_PATHS`, `LocaleMiddleware` and the `LANGUAGES` list in settings → optionally re-add `User.preferred_language` + `set_language`. The trans markers are already in place, so no template/code churn.

**Verification:** full CI-faithful suite green — **1051 passed / 1 skipped / 1 xfailed** (baseline unchanged: no test touched translations; `makemigrations --check` clean). Live at :3030: stack rebuilt, **migration 0254 applied cleanly**; login as a throwaway user → plain redirect to `/2fa-prompt` with **no `django_language` cookie set**; `/preferences/profile/` renders without the Language control (timezone/theme intact); profile-save POST → 302 to the user page with values persisted; password-change flow OK; the `LoginWith2FA` call site is covered by its six suite tests. Throwaway user hard-deleted — note: `User.delete()` is a **soft delete** ("we don't actually delete the database entry": deactivates + erases data), so a true removal needs queryset-level `User.objects.filter(...).delete()` after clearing ShelfFilm/Shelf/UserSession. DB back to exactly 2 users, all other counts at baseline (Film 1,381 / Status 4 / Review 2 / Shelf 4 / ShelfFilm 1,380).

**Owner note (2026-09-03):** the current live-DB contents are **disposable test data**, not precious production data — the earlier "never wipe" constraint is relaxed accordingly.

## 5. What still needs to be done

### Milestone 2 — pushed ✅ (2026-08-30)

Owner approved and the milestone-2 commits went out to the `fork` remote (fast-forward, no force). Fork main = `a00c7cd1e`. The local instance is already running this exact code + migrations 0247→0249.

### Milestone 3 — pushed ✅ (2026-08-31)

Owner approved and the milestone commits went out to the `fork` remote (fast-forward, no force) on 2026-08-31. Fork main = `a0342a3c0`. The live instance is already running this exact code with the TMDB key configured in `.env`.

All four design decisions were aligned with the owner up front (§8 #21–24); implementation is in `e709614e2` + `e9bd0b007` (details in §4).
- **Live verification at :3030 (2026-08-30), throwaway user:** not-configured notice confirmed *before* the key was set; after adding `REELTALK_TMDB_API_KEY` to the live `.env` — search rendered 15 results with posters; add-new-film → Want to Watch (full metadata + poster populated); re-search showed the "In your library" badge linking to the film page; duplicate shelf add rejected ("is already on Want to Watch"); title/year backfill worked (manually created *The Godfather* 1972 got tmdb_id 238 + director/genres/poster, no duplicate row); list target added with correct ordering and duplicate list add rejected; both entry points render (preferences sidebar, list page); film page shows "View on TMDB". Throwaway user hard-deleted afterwards — live DB back to its original state (2 users / 0 films).
- **Next milestone:** the search UX rework below (owner-directed 2026-08-31), then the remainder (artwork, Crowdin, public deploy, file-based import).

### Search UX rework — executed ✅ (2026-08-31), pushed 2026-09-01

Executed per the plan below in three commits (`c7c920737`, `8832a5a8e`, `710e18038`) — full execution record, test baseline and live verification results are in §4. The spec and design decisions are kept here as the decision record (decision log #25).

Owner redirect after reviewing milestone 3: TMDB should be the **primary film catalog** (Letterboxd model — the owner confirmed Letterboxd uses TMDB as the source of all its film data), reached from the **main search box**, not from a Settings→Import page. "Import" is reserved for actual file-based imports (e.g., a CSV exported from TMDB) — that's a future milestone, not this one.

**Owner spec:** typing "Blade Runner" in the main search box at the top of the page should list films titled Blade Runner **from the TMDB database**. Each result offers an **"Add to Watchlist"** button next to the title, OR clicking the film opens its page with more info and an "Add to Watchlist" action there. Rename **"Want to Watch" → "Watchlist"** everywhere (the user's watchlist = films they want to watch later).

**Design decisions (owner-approved 2026-08-31, decision log #25):**
1. Global film search queries TMDB when `REELTALK_TMDB_API_KEY` is set; falls back to the existing local trigram search when unset (graceful degradation per #22). User/list search and the federated API endpoint (`api_film_search`) are unchanged — the API stays local-only.
2. Result rows: TMDB poster + title + year. The title links to a click-through route that creates-or-matches the local Film on first click (reusing `ensure_local_film` / backfill logic) and redirects to the film page. "Add to Watchlist" is a one-click POST (create-or-match + shelve onto the TO_READ shelf), then re-renders the search with an "On your watchlist" state on that row. Anonymous users see results but no add button; shelves exist only for local users.
3. The film page already has the shelf selector (`snippets/shelf_selector.html`) — its "Want to Watch" label simply becomes "Watchlist"; no new control needed there.
4. **Remove** the `/import/` page, its URL, both entry points (preferences sidebar link, list-page "Or search TMDB…" link) and `tests/views/test_import_films.py`. Move the reusable logic (`find_local_film`, `ensure_local_film`, `backfill_film_from_tmdb`, `add_poster`) from `views/import_films.py` into `reeltalk/tmdb.py`; drop the list-target code (`get_target_choices`/`resolve_target`/`add_to_target`). The `set_list_item_order` extraction in `views/list/list.py` STAYS — `add_film` uses it.
5. Rename scope: `create_shelves` default name → "Watchlist"; a **data migration** renaming existing shelves with identifier="to-read" from "Want to Watch" → "Watchlist" (the identifier is wire format — unchanged); template strings (`templates/user/user.html`, `snippets/shelf_selector.html`); tests asserting the old name (e.g. `tests/views/test_feed.py`). `views/helpers.py:159` ("wants to watch") is a status phrase, not a shelf name — leave it.

**Implementation notes:**
- `film_search()` in `views/search.py` currently does local trigram search via `book_search.search()`; swap the film branch for `tmdb.search_films()` with per-row local-match annotation (`find_local_film`) + watchlist state; pass `page` through to TMDB (it returns up to 20/page).
- New routes: GET click-through (e.g. `/search/film/<tmdb_id>/` → ensure film → redirect to `film.local_path`) and a POST watchlist action (login required, local users only; hidden `return_to` field preserves the results grid after adding).
- `templates/search/film.html` needs a TMDB-results branch (CDN posters — the Search view already has `@csp_update(IMG_SRC="*")`) alongside the legacy local-results markup for fallback mode.
- Suggested commits: (1) Watchlist rename + data migration, (2) TMDB global search + click-through + watchlist action (+ tests), (3) import-page removal. Then: full suite green via the CI-faithful flow (§7; baseline 998), PROGRESS.md update, live rebuild + click-through per the owner spec above, push to `fork` after owner review.
- Letterboxd reference points (confirmed with owner): catalog = TMDB with no user-created films on their side; search results carry a one-click Watchlist action; the film page shows all TMDB data with rating/diary/watchlist actions; "Import" is a separate file-based data feature (CSV export/import).

**Optional if time permits:** the six flagged app nits in §4 (viewer_aware_objects Manager, Status.delete quotation attr, Quotation.pure_content regex, ShelfFilm.save latent crash, get_rating soft-delete count, link-domains "book pages" wording) — each is small and owner-blessed to fix opportunistically.

**Known small gaps found during the sweep (non-blocking, fix opportunistically):**
- ~~`user.shared_books` is referenced in `directory/user_card.html` + `groups/suggested_users.html` but no longer exists on User~~ — ✅ **Resolved 2026-09-03** (`daa64522b`): both suggested-users surfaces now annotate `shared_films` (films on both users' shelves) and the directory user card + group/feed snippets render it.
- Guided-tour search steps were re-anchored to the new `tour-*-film*` ids, but the tour copy still describes the old flow; polish with the owner if the tour matters for alpha.

- If the host's LAN IP changes again: update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in the live `.env`, then `docker compose up -d && docker compose restart nginx` (see §7 quirks).

### Phase 2 — remainder (DESIGN WITH THE OWNER FIRST; no solo design decisions)
Milestones 1–3 and the search UX rework are done and pushed. What remains, from PLAN.md §12 plus the owner's 13-item list (plus the owner-reported backlog below):
- **File-based film import** — ✅ **Done 2026-09-02, PUSHED to fork 2026-09-03.** "Import" was reserved for this by decision #25; design settled with the owner (decisions #29–32): TMDB-style CSVs only, no API calls during import, synchronous per-row results, export round-trips, async TMDB backfill of posters/details after import. `aea3e497c` + `01e179539` + `694c621eb` — execution records in §4. The owner has since imported their 1,378-film watchlist into the live instance (backfilled per #32) — now confirmed **disposable test data** (owner, 2026-09-03).
- Custom ReelTalk artwork replacing BookWyrm's placeholder/wyrm imagery.
- ~~Re-point `locale/**` at a ReelTalk Crowdin project~~ — ✅ **Resolved 2026-09-03 by removal instead (decision #34):** the whole Crowdin/translation component is gone; English-only for now. Re-introduction = new Crowdin project + crowdin.yml + makemessages (full path in §4).
- Public instance deployment of the alpha (operator's own TLS proxy in front of :3030).

### Owner-reported issues (2026-09-01, from live use of the search rework)

Owner exercised the new search flow on the live instance (added *Camp Hideaway Massacre* to Watched and reviewed it) and reported three issues. Status 2026-09-01:

1. **Search-as-you-type dropdown** (feature request) — ✅ **Done, suite + live-verified, PUSHED to fork 2026-09-02** after owner review. Implemented per decision #28 (`de929e896` + `6c7658b8c`, fixes in `2a112670f`/`607cad2fa` — execution record in §4). Spec below. Owner then reported a poster-display defect → issue 4 below.
2. **TMDB metadata is not user-editable** (decision #26) — ✅ Done, live-verified (`f98542481`, execution record in §4). Scope as confirmed: lock only films with a `tmdb_id`; manually created films stay fully editable. Only user-generated content remains editable (review title/body, star rating, comments/interactions).
3. **One review per film** (decision #27) — ✅ Done, live-verified (`5acf6a3be`, execution record in §4). The live duplicate of *Camp Hideaway Massacre* had been cleaned up earlier (review id 11 deleted; earliest review id 8 kept), which served as the live test case.
4. **Suggest-dropdown posters render only half / sometimes not at all** (bug, reported by owner 2026-09-02; screenshot `/home/minnix/search_box.jpg`) — ✅ **Done, suite + live-verified, PUSHED to fork 2026-09-02** after owner review. Two root causes, both fixed CSS/JS-only (`5397f486a` + `fb4cf48b7`, execution record in §4): (a) Bulma's `.navbar-item img { max-height: 1.75rem }` logo cap was clamping the posters because the search form is a `.navbar-item` → `max-height: none` on `.search-suggest-poster img`; (b) `loading="lazy"` inside the scrollable menu left some posters unloaded in Chromium → dropped (rows capped at 8).

**Issue 1 — agreed spec (decision #28, owner-aligned 2026-09-01; Letterboxd model):**
- **Suggest endpoint:** `GET /search/suggest/?q=<term>&type=film` returning JSON. With `REELTALK_TMDB_API_KEY` set it queries TMDB's `search/movie` (reusing `tmdb.search_films()`, page 1, top ~8 hits); when unset it falls back to the local trigram search — same graceful degradation as decision #25. Each result: title, year, poster (TMDB CDN or local), and a link target — local matches go straight to the film page; TMDB-only hits reuse the existing click-through route `GET /search/film/<tmdb_id>/` (create-or-match + redirect).
- **Rows stay minimal:** title + year + poster only — **no inline "Add to Watchlist"** in the dropdown (owner confirmed). Clicking a row navigates to the film page, where the user can watchlist it or review it.
- **Local users only:** the endpoint returns nothing for anonymous users; no suggestions are shown to them (owner confirmed).
- **Client:** small vanilla-JS handler on the main search box (no new dependencies): ~300 ms debounce, minimum 2 characters, dropdown rendered under the input; **click-only — no keyboard navigation** (owner confirmed fine for alpha); Enter still submits the normal full search.
- **No-key local-fallback behavior:** the dropdown lists local-library matches only (there is no TMDB catalog to query); with zero local matches it shows nothing — no "no results" noise while typing. Consistent with how the full search page degrades.

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
5. **The live `.env` TMDB key leaks into test runs:** `docker compose run` inherits the project's `.env`, so `REELTALK_TMDB_API_KEY` is set inside the test container on this host. Global film search branches on that key, so tests asserting local-fallback behavior pin `TMDB_API_KEY=''` via `override_settings` (TMDB-mode tests set `'test-key'`). If a future session sees unmocked `api.themoviedb.org` calls in tests, that's why — GitHub CI has no key and behaves the same as the pinned tests.
6. **The `media_volume` named volume persists between test runs:** uploads saved by one run (e.g. `/app/images/uploads/user_1/1/240.jpg`) are still there for the next, so Django's storage suffixes re-saved filenames (`240_MuQ6bzv.jpg`). Tests must never assert exact upload URLs — build expectations from the stored file's `.url` (done in `test_status.py` 2026-09-01). GitHub CI is unaffected (fresh volume per run).

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
- **Green baseline:** **1051 passed / 1 skipped / 1 xfailed** (~3.5 min with `-n 3`) — unchanged after the Crowdin/translation removal (2026-09-03; no test touched translations), same as after the structural correctness audit + Quotation removal (2026-09-03). Previous baselines: 1050 after the async TMDB backfill (2026-09-02; +7 tests), 1043 after the file-based film import (2026-09-02; +1 login regression + 13 import tests, export tests rewritten in place), 1029 after owner-reported issue 1 (2026-09-01; +12 suggest tests + 1 poster-URL regression), 1017 after issues 2+3 (+18 tests: 11 film page/edit, 5 status/review, 2 finish-flow), 999 after the search UX rework (2026-08-31), 998 milestone 3, 975 milestone 2 (the drop from 1332 was removed-feature coverage: connectors, importers, book views, imports, readwise, ISNI, suggestion lists, series, cover jobs).

### After changing app code
`docker compose up -d --build` (rebuilds all app images), then `docker compose restart nginx` (quirk #1), then wait for web healthy.
- **Per-service images:** web, celery_worker and celery_beat each have their own image tag (`reeltalk-work-web`, `reeltalk-work-celery_worker`, …). `up -d --build <one service>` does NOT update the others — a worker on the old image silently drops new tasks as "unregistered" (hit this with the backfill task, 2026-09-02). When adding or changing Celery tasks, rebuild web + celery_worker + celery_beat.

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
13. **Flat single `Film` model** (2026-08-25): one object per title. The Work/Edition split, edition picker, ISBN dedup, and edition ranking are all dropped; statuses, shelves, and lists anchor directly to Film.
14. **People as plain fields** (2026-08-25): directors/cast are name lists on Film — no Person model, no person pages; the Author model is dropped with it.
15. **New `"Film"` AP wire type** (2026-08-25): clean break from the Book/Edition/Author wire types; film objects federate between ReelTalk instances only.
16. **Data-migrate the local instance to Film** (2026-08-25): existing book rows convert to films and statuses/shelves/lists re-point; URLs move `/book/<id>` → `/film/<id>`.
17. **Binary watch state, no in-progress analogs** (2026-08-26): "there's only two statuses when it comes to films" — seen or not-yet-seen-but-wished. No started/finished-reading equivalents; the Currently Watching / Stopped Watching shelf presets and their status headers are removed.
18. **Silent watched** (2026-08-26): marking a film watched posts **no** auto-generated note ("Post to feed" checkbox removed from the finish modal). Sharing a watched film happens via reviews/ratings, which the finish flow creates.
19. **Watched requires a rating** (2026-08-26): a film cannot be added to Watched without a star rating (out of 5); the written review is optional. Rating-only entries are stored as `ReviewRating`.
20. **Letterboxd as loose design template** (2026-08-26): the owner models ReelTalk's UX loosely on Letterboxd; use it as the reference when aligning on future design decisions together.
21. **TMDB as the import API** (2026-08-30): TMDB v3 REST over OMDb — genres/directors/cast/poster/year/runtime map 1:1 onto Film fields; tmdb_id is already the primary dedup field and the film page links out to themoviedb.org.
22. **API key in `.env`** (2026-08-30): `REELTALK_TMDB_API_KEY`, operator-set, shared by all users; when unset the import page shows a not-configured notice (no SiteSettings field, no per-user keys).
23. **Dedup = ID + title/year fallback** (2026-08-30): search hits already in the library get an "In your library" badge and add directly; manually created films matching normalized title + year get `tmdb_id` backfilled and empty metadata filled — no duplicate rows (Letterboxd disambiguates its search the same way).
24. **Scope = core + shelf targets** (2026-08-30): one import page; destination = any of the user's lists OR the Want to Watch shelf (Letterboxd-style watchlist target); Watched is not a destination (rating required, #19); bulk TMDB-watchlist import is out.
25. **TMDB as primary catalog via global search; "Watchlist" rename** (2026-08-31): the main search box queries TMDB (Letterboxd model — owner confirmed they use TMDB as the source of all film data); results offer one-click "Add to Watchlist" and click-through to the film page; the Settings→Import Films page is removed ("Import" reserved for future file-based imports, e.g. a CSV exported from TMDB); "Want to Watch" is renamed to "Watchlist" everywhere (display name only — the shelf identifier stays `to-read`). Supersedes the UX shape of #24 (the create-or-match/backfill mechanics survive in the search flow).
26. **TMDB is the source of truth for film metadata; it is not user-editable in the UI** (2026-09-01): only user-generated content stays editable (review title/body, star rating, comments/interactions); TMDB-sourced fields on the film page must be locked. **Scope confirmed by owner 2026-09-01: lock only films with a `tmdb_id`; manually created films (no TMDB ID) stay fully editable** — they have no external source of truth.
27. **One review per film** (2026-09-01): if a user has already reviewed a film, the UI offers editing that review only — no second review. (Reported live: the Home Timeline "Your Films" panel allowed a duplicate review of *Camp Hideaway Massacre*.)
28. **Search-as-you-type dropdown design** (2026-09-01): `GET /search/suggest/?q=<term>&type=film` JSON endpoint — TMDB when the key is set (top ~8 of page 1 via `tmdb.search_films()`), local trigram fallback when unset; rows are minimal (title + year + poster, **no inline watchlist action**); **local users only** (anonymous users get no suggestions); **click-only** — clicking navigates to the film page (local match → film page; TMDB-only hit → existing click-through route), where watchlisting/reviewing happens. Vanilla JS on the main search box, ~300 ms debounce, min 2 chars, Enter still submits the normal search; no-key mode shows local matches only and nothing when there are zero.
29. **File-based import format and entry point** (2026-09-02): "Import" (reserved by #25) accepts **TMDB-style CSVs only** — the canonical ten-column header is TMDB's own export shape (the owner's watchlist export is the reference), and ReelTalk's "Export Film List" emits the same format so exports round-trip. Entry point: Preferences → Data → "Import Film List" (`/preferences/import/`), local users only; synchronous single-transaction import with a per-row results table + summary (no background job).
30. **File-based import semantics** (2026-09-02): **no TMDB API calls** during import — the CSV is self-sufficient. Per row: create-or-match ID-first (TMDb ID, then IMDb ID), then normalized title + year (#23); on match, empty local IDs/year backfilled. Unrated row → film added to Watchlist; rated row → TMDB's 1–10 `Your Rating` mapped ÷2 onto the 5-star scale (nearest half star) → Watched + `ReviewRating` (#19). Existing reviews are never touched (#27); non-movie rows (`Type` ≠ movie) and missing-name rows are skipped with a note. All saves use `broadcast=False` — importing your own data is not federation.
31. **Export Film List mapping** (2026-09-02): one row per film the user has a relationship with (shelved / reviewed / commented / quoted), in the canonical TMDB ten-column format: TMDb + IMDb IDs from the film, `Type` = "movie", Release Date = stored year as `YYYY-01-01T00:00:00Z`, Your Rating = most recent rated review ×2, Date Rated from that review's published date (UTC); season/episode and community-score columns empty; review text drops out (the format carries ratings, not reviews).
32. **Async TMDB backfill for imported films** (2026-09-02): the file import creates ID stubs (no API calls, #30), so a background Celery task now runs after each import and fetches TMDB details + poster for every imported film (created **and** matched — re-importing self-heals leftover stubs). Rate-limit-friendly pacing (~15 min for 1,378 films), idempotent (skips films that already have a poster + description), per-film failures skipped and logged, no-op without an API key. Result: the watchlist looks complete without any user action (Letterboxd model). Triggered by the owner reporting blue placeholder boxes on their imported films.
33. **Quotation feature removed entirely** (2026-09-03): book-era holdover — it is quoting a line *from* a book (not one user quoting another in a reply, which is the Reply tab). Film users don't add quotes from films; only reviews and star ratings. Removed end-to-end: model + MTI table (migration 0251), AP wire type, feed-filter choices (migrations 0252–0253), views/forms/templates/tests; inbound remote Quotation activities are gracefully skipped via the `naive_parse` ignore list.
34. **Crowdin/translation component removed; English-only for now** (2026-09-03): the owner may ask volunteers to translate later, so removal must be clean and re-introduction easy — "re-adding = new Crowdin project + crowdin.yml + makemessages". Removed: `crowdin.yml` + `locale/` (49 BookWyrm-era catalogs), settings i18n wiring (`LOCALE_PATHS`, `LANGUAGE_COOKIE_NAME`, `LocaleMiddleware`, the `LANGUAGES` list; `LANGUAGE_CODE` pinned to `en-us`), `User.preferred_language` (migration 0254) + form field + template control, and the `set_language()` helper with its five call sites (now plain redirects). Kept: all `{% trans %}`/gettext markers (no-ops without catalogs — stripping would be churn that makes re-adding harder), `USE_I18N = True`, nodeinfo's `"languages": ["en"]`, and the gettext dev deps + `rt-dev` locale subcommands (the re-add toolchain).
