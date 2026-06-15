# algo-reel

LLM-driven illustrative video generator (backend, milestone 1).

See [docs/trd.md](docs/trd.md) for the full TRD and [docs/superpowers/specs/2026-05-19-algo-reel-m1-design.md](docs/superpowers/specs/2026-05-19-algo-reel-m1-design.md) for the M1 design.

## Quick start

```bash
cp .env.example .env
make install
make up           # start postgres + redis
make migrate
make render-image       # build the ffmpeg/trivial render container (M4)
make render-image-manim # build the Manim render container (M5) — required for renderer=manim
make dev          # API, in one shell
make worker       # orchestrator pool, in another shell
make render-worker # render pool, in a third shell
```

Running a video with `renderer=manim` requires **both** `make worker` (orchestrator) and `make render-worker` (render pool) to be running simultaneously.

## Job lifecycle

Jobs transition through: `queued → scripting → script_ready → rendering → composing → done`.

If one or more scenes fail to render but others succeed, the job lands in `partially_failed` instead of `failed`. A `partially_failed` job can be retried without re-running the whole pipeline via `POST /api/videos/{id}/resume`, which re-queues only the failed scenes and transitions the job back to `rendering`. See [docs/apis/videos.md](docs/apis/videos.md) for the full endpoint reference.

## Tests

```bash
make test
```

## Smoke tests

Gated integration tests that hit real external services or Docker images:

```bash
make smoke-render  # trivial ffmpeg render through algoreel-render:m4 image
make smoke-manim   # full Manim render + mux through algoreel-manim:m5 image (Docker required)
make smoke-llm     # live LLM call (requires ALGOREEL_ALLOW_LIVE_LLM=1 implicitly via make)
make smoke-tts     # live TTS call
```

`make smoke-manim` builds inputs, runs the canned Manim scene through the hardened sandbox (read-only fs + tmpfs + uid 10001 + network=none), muxes the result, and asserts `scene.mp4` is non-empty. Use this to verify the Docker image is correct after rebuilding.
