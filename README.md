> ## ⛔ FROZEN — 2026-09-04
>
> This repository is **frozen as a reference-only copy** of the original ReelTalk (the BookWyrm fork under the Anti-Capitalist Software License v1.4). It will not receive further development and is archived on GitHub.
>
> The project continues as a **ground-up rewrite under AGPLv3** at **[minnixtx/reeltalk](https://github.com/minnixtx/reeltalk)**. Use this repository only as a functional reference (feature inventory, behavior, design decisions — see [PROGRESS.md](PROGRESS.md)); do not copy code from it into the new project.

# ReelTalk

A federated social network for tracking, reviewing, and discovering films.

ReelTalk is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) — the open-source, ActivityPub-based social network for books — reimagined for film fans: B-movies, cult classics, midnight shows, double features, and everything in between. The name is a pun on "real talk": honest conversation, anchored to the reel.

## Status

🚧 **Alpha.** Phase 1 (rebrand + simplified Docker self-hosting) and the film domain rework are complete: books/editions/authors have been replaced by a flat film model (title, year, runtime, cast, directors, genres, poster), the UI is fully film-first with binary watch state (Watchlist / Watched — marking a film watched requires a star rating), and TMDB is the primary film catalog: the main search box queries TMDB directly, with one-click "Add to Watchlist" and click-through to film pages. Federation runs over a new `Film` ActivityPub wire type between ReelTalk instances. Search-as-you-type suggestions (with posters) and file-based import/export of TMDB-style CSVs — including an automatic background backfill of metadata and posters for imported films — are also in; the site is currently English-only. Next up: custom ReelTalk artwork and a first public instance (design work with the owner, at the very end). See [PROGRESS.md](PROGRESS.md) for the full milestone history and owner decision log.

## What ReelTalk will be

- 🌐 **Federated** — built on ActivityPub; instances can follow each other across the fediverse
- 🎬 **Film-first** — track what you've watched, rate it, write reviews, and build shelves of favorites
- 👥 **Community-driven** — small, trusted communities instead of one giant feed
- 🔓 **Free and open source** — no corporate middleman

## Self-hosting (alpha)

Requirements: [Docker](https://docs.docker.com/get-docker/) with the Compose plugin.

```sh
git clone https://github.com/minnixtx/reeltalk
cd reeltalk
cp .env.example .env
./setup.sh                 # generates SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD; asks for DOMAIN
docker compose up -d --build
```

- `DOMAIN` must be the hostname users will reach the instance at.
- **TLS is your responsibility:** the stack exposes a plain-HTTP endpoint at `http://<host>:3030` (override with `WEB_PORT` in `.env`). Terminate TLS with your own reverse proxy and point it at that port, forwarding `X-Forwarded-Proto: https`.
- **Email (optional):** the site runs without SMTP; to enable it, uncomment the `EMAIL_*` block in `.env`.

## Tech stack

- [Django](https://www.djangoproject.com/) web backend
- [PostgreSQL](https://www.postgresql.org/) database
- [ActivityPub](http://activitypub.rocks/) federation
- [Celery](https://docs.celeryproject.org/) task queue + [Redis](https://redis.io/) (single container: streams/cache on DB 0, Celery broker on DB 1)
- Django templates, [Bulma.io](https://bulma.io/), vanilla JavaScript
- [Docker](https://www.docker.com/) Compose deployment, [Gunicorn](https://gunicorn.org/), [Nginx](https://nginx.org/en/) (plain-HTTP endpoint; TLS via your own proxy)

## Roadmap

- [x] Project seed
- [x] Full fork + rebrand of BookWyrm (Phase 1)
- [x] Film domain model (titles, years, cast, ratings)
- [x] Metadata integration (TMDB as the primary film catalog via global search)
- [x] File-based film import/export (e.g. a CSV exported from TMDB, with background metadata backfill)
- [ ] Custom ReelTalk artwork
- [ ] First public instance

## License

[Anti-Capitalist Software License v1.4](LICENSE.md), © 2020 Mouse Reeve. ReelTalk is a derivative work of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm); the license text and attribution are preserved in full.
