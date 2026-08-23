# ReelTalk

A federated social network for tracking, reviewing, and discovering films.

ReelTalk is a fork of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm) — the open-source, ActivityPub-based social network for books — reimagined for film fans: B-movies, cult classics, midnight shows, double features, and everything in between. The name is a pun on "real talk": honest conversation, anchored to the reel.

## Status

🚧 **Alpha.** Phase 1 (rebrand + simplified Docker self-hosting) is complete; the codebase currently runs BookWyrm's book-centric feature set under the ReelTalk name. The film domain model (titles, years, cast, ratings — replacing books/editions/authors) is the next phase and will be designed with the community.

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
- [ ] Film domain model (titles, years, cast, ratings)
- [ ] Metadata integration (TMDB)
- [ ] Custom ReelTalk artwork
- [ ] First public instance

## License

[Anti-Capitalist Software License v1.4](LICENSE.md), © 2020 Mouse Reeve. ReelTalk is a derivative work of [BookWyrm](https://github.com/bookwyrm-social/bookwyrm); the license text and attribution are preserved in full.
