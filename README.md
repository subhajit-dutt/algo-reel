# algo-reel

LLM-driven illustrative video generator (backend, milestone 1).

See [docs/trd.md](docs/trd.md) for the full TRD and [docs/superpowers/specs/2026-05-19-algo-reel-m1-design.md](docs/superpowers/specs/2026-05-19-algo-reel-m1-design.md) for the M1 design.

## Quick start

```bash
cp .env.example .env
make install
make up           # start postgres + redis
make migrate
make render-image # build the render container once
make dev          # API, in one shell
make worker       # orchestrator pool, in another shell
make render-worker # render pool, in a third shell
```

## Tests

```bash
make test
```
