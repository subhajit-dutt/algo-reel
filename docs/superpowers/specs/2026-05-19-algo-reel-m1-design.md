# Algo-Reel Milestone 1 — API + DB + Job Model

**Status:** Approved (brainstorming)
**Owner:** Subhajit Dutta
**Date:** 2026-05-19
**Related:** [docs/trd.md](../../trd.md)

---

## 1. Purpose

Build the foundation of the algo-reel backend: a FastAPI service, Postgres schema, and an Arq-based job queue that walks a stubbed video-generation job through its full lifecycle. No real LLM, TTS, or rendering yet — those layers land on top of this foundation in subsequent milestones without architectural rework.

This milestone is "done" when:

- A bearer-authenticated client can `POST /api/videos`, observe the job transition through every status via `GET /api/videos/{id}`, and `DELETE` to cancel mid-flight.
- Two processes are running locally (FastAPI + Arq worker) backed by Postgres and Redis via `docker-compose`.
- Every status transition is persisted and emitted as a structured log line.
- Integration tests cover the API + worker against a real Postgres + Redis.

---

## 2. Scope

### In scope

- FastAPI app (async, Pydantic v2)
- Postgres schema: `jobs`, `scenes`, `renders`, `assets` (last two persisted-but-empty in M1)
- SQLAlchemy 2.0 async + Alembic migrations
- Arq worker + Redis queue, wired end-to-end
- Orchestrator stub: walks a job `queued → scripting → script_ready → rendering → composing → done` on `asyncio.sleep` placeholders, persisting at every transition
- Bearer-token auth (single shared secret via `.env`)
- Endpoints: `POST /api/videos`, `GET /api/videos/{id}`, `DELETE /api/videos/{id}`, `GET /healthz`, `GET /readyz`
- structlog → stdout, every line carries `job_id`
- `docker-compose.yml` for local Postgres + Redis
- `.env.example` documenting the full future env surface
- Integration tests against real PG + Redis (`testcontainers`)

### Out of scope (deferred — see §11 Future Scope)

LLM script generation, TTS, Manim/AI-image renderers, FFmpeg concat, object storage, SSE progress endpoint, script inspect/edit, resume endpoint, cost circuit breaker, dead-letter queue, content-retry loop, backpressure 429s, Prometheus/OTel/Grafana, frontend.

---

## 3. Architecture

```
┌──────────────────┐      enqueue       ┌──────────────────┐
│ FastAPI (api)    │ ─────────────────▶ │ Redis (arq queue)│
│ uvicorn          │ ◀───────────────── │                  │
└──────────────────┘    pub/sub later   └────────┬─────────┘
        │                                        │ dequeue
        │ SQLAlchemy async                       ▼
        │                               ┌──────────────────┐
        │                               │ Arq worker       │
        │                               │ (orchestrator    │
        │                               │  pool, 1 proc)   │
        │                               └────────┬─────────┘
        │                                        │ SQLAlchemy async
        ▼                                        ▼
                       ┌──────────────────┐
                       │ Postgres         │
                       │ jobs/scenes/...  │
                       └──────────────────┘
```

### Process topology

- **api**: `uvicorn app.main:app` — serves HTTP, persists job rows, enqueues Arq jobs. Never executes orchestrator work.
- **worker (orchestrator pool)**: `arq app.workers.arq_settings.WorkerSettings` — single queue `orchestrator_pool`. The render pool (separate Arq worker on `render_pool` queue) is introduced in M4; reserved name only in M1.

The two-process split is non-negotiable per TRD §4.2 — rendering Manim inside the FastAPI process would block the event loop and OOM the API. M1 puts the boundary in place before there's any CPU work to isolate, so M2/M4 only swap the stub body.

### Request → enqueue flow

1. `POST /api/videos` → validate body → insert `jobs` row with `status='queued'` → `arq.enqueue_job('run_video', job.id)` → store `arq_job_id` on the row → return `202 Accepted` + `JobResponse`.
2. Arq worker dequeues, runs `run_video(ctx, job_id)`. See §6 for the state machine.
3. `GET /api/videos/{id}` reads the current row + ordered scenes; the worker is the only writer of `status`/`progress`/`scenes[*].status`.
4. `DELETE /api/videos/{id}` writes `status='cancelled'`; worker observes this at each checkpoint.

---

## 4. Folder structure

```
algo-reel/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI factory, lifespan, route mount
│   ├── config.py                  # pydantic-settings; reads .env
│   ├── deps.py                    # FastAPI dependencies: db session, auth
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                # bearer-token verifier
│   │   ├── videos.py              # POST/GET/DELETE /api/videos
│   │   └── health.py              # GET /healthz, /readyz
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py             # async engine + session factory
│   │   ├── base.py                # DeclarativeBase
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── job.py
│   │       ├── scene.py
│   │       ├── render.py
│   │       └── asset.py
│   │
│   ├── schemas/                   # Pydantic request/response models (HTTP boundary)
│   │   ├── __init__.py
│   │   ├── job.py                 # CreateJobRequest, JobResponse
│   │   └── scene.py               # SceneResponse
│   │
│   ├── domain/                    # business types shared with PydanticAI (M2+)
│   │   ├── __init__.py
│   │   ├── enums.py               # JobStatus, SceneStatus, Renderer, AssetKind
│   │   └── script.py              # Scene, VideoScript (placeholder in M1)
│   │
│   ├── repositories/              # all DB access; SRP, one repo per aggregate
│   │   ├── __init__.py
│   │   ├── job_repo.py
│   │   └── scene_repo.py
│   │
│   ├── services/                  # orchestration logic; no direct DB queries
│   │   ├── __init__.py
│   │   └── job_service.py         # create_job, cancel_job, get_job
│   │
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── arq_settings.py        # WorkerSettings: queue name, funcs, redis url
│   │   └── orchestrator.py        # run_video stub: state-machine walker
│   │
│   └── logging.py                 # structlog config
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_init.py           # initial schema (jobs/scenes/renders/assets)
├── alembic.ini
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pg+redis fixtures via testcontainers
│   ├── api/
│   │   └── test_videos.py
│   ├── workers/
│   │   └── test_orchestrator.py
│   └── repositories/
│       └── test_job_repo.py
│
├── docker-compose.yml             # postgres + redis services
├── Dockerfile                     # app image (parity for CI / future prod)
├── pyproject.toml                 # uv-managed
├── uv.lock
├── .env.example
├── .env                           # git-ignored
├── .gitignore
├── Makefile                       # dev / worker / migrate / test / fmt targets
├── README.md
├── CLAUDE.md                      # existing
└── docs/
    ├── trd.md
    └── superpowers/
        └── specs/
            └── 2026-05-19-algo-reel-m1-design.md
```

The sample `main.py` at the project root is deleted.

### Layering rules

- One-way dependency arrow: `api/` → `services/` → `repositories/` → `db/models/`. Routers never touch the ORM directly.
- `schemas/` (HTTP), `db/models/` (ORM), `domain/` (PydanticAI) are three distinct sets of types. Conversion happens at the edges.
- `services/` is the only layer that calls `arq.enqueue_job`. Repositories don't know the queue exists.
- `workers/orchestrator.py` reuses `repositories/` and `services/`. No duplicate DB access between API and worker.

---

## 5. Data model

All tables use `id SERIAL PRIMARY KEY` (per CLAUDE.md). Every table has `created_at TIMESTAMPTZ NOT NULL DEFAULT now()` and `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (omitted from columns below). All child FKs `ON DELETE CASCADE` from job.

Status columns use `text` + `CHECK` constraints, not Postgres `ENUM` — adding a value via `ALTER TYPE` is a noisier migration than swapping a CHECK.

### `jobs`

| Column | Type | Notes |
|---|---|---|
| `id` | `serial PK` | |
| `user_prompt` | `text NOT NULL` | |
| `renderer` | `text NOT NULL CHECK (renderer IN ('manim','ai_image'))` | |
| `voice` | `text NOT NULL DEFAULT 'alloy'` | |
| `duration_target_seconds` | `integer NOT NULL CHECK (duration_target_seconds IN (30,60,180))` | TRD §10.2 tiers |
| `status` | `text NOT NULL` | CHECK in (`queued, scripting, script_ready, rendering, composing, done, failed, cancelled, partially_failed`) |
| `progress` | `jsonb NOT NULL DEFAULT '{}'` | `{"current_scene": int, "total": int, "stage": str}` |
| `script` | `jsonb` | nullable; populated M2 |
| `output_url` | `text` | nullable; final MP4 signed URL |
| `cost_usd` | `numeric(10,4) NOT NULL DEFAULT 0` | stays 0 in M1 |
| `error` | `jsonb` | nullable; `{type,message,trace,attempt}` |
| `attempts` | `integer NOT NULL DEFAULT 0` | Arq infra-retries |
| `arq_job_id` | `text` | nullable; arq's id |

Index: `ix_jobs_status_created_at (status, created_at DESC)`.

### `scenes`

| Column | Type | Notes |
|---|---|---|
| `id` | `serial PK` | |
| `job_id` | `int NOT NULL REFERENCES jobs(id) ON DELETE CASCADE` | |
| `index` | `integer NOT NULL` | order within video |
| `narration` | `text NOT NULL` | |
| `visual_prompt` | `text NOT NULL` | |
| `manim_code` | `text` | nullable; Manim path |
| `image_prompts` | `jsonb` | nullable; AI-image path |
| `duration_seconds` | `numeric(6,2) NOT NULL` | from TTS in M3; placeholder in M1 |
| `status` | `text NOT NULL` | CHECK in (`pending, rendering, done, failed`) |
| `output_url` | `text` | nullable |

Constraint: `UNIQUE (job_id, index)`.

### `renders` (attempt audit trail — empty in M1)

| Column | Type | Notes |
|---|---|---|
| `id` | `serial PK` | |
| `scene_id` | `int NOT NULL REFERENCES scenes(id) ON DELETE CASCADE` | |
| `attempt` | `integer NOT NULL` | 1, 2, 3 |
| `status` | `text NOT NULL` | CHECK in (`started, succeeded, failed`) |
| `stderr` | `text` | nullable |
| `duration_ms` | `integer` | nullable |
| `cost_usd` | `numeric(10,4) NOT NULL DEFAULT 0` | |

Index: `ix_renders_scene_attempt (scene_id, attempt)`.

### `assets` (object-storage pointer table — empty in M1)

| Column | Type | Notes |
|---|---|---|
| `id` | `serial PK` | |
| `job_id` | `int NOT NULL REFERENCES jobs(id) ON DELETE CASCADE` | |
| `scene_id` | `int REFERENCES scenes(id) ON DELETE CASCADE` | nullable; null = job-level asset |
| `kind` | `text NOT NULL` | CHECK in (`audio, scene_mp4, final_mp4, image, manim_log`) |
| `storage_key` | `text NOT NULL` | |
| `bytes` | `bigint` | nullable |
| `content_type` | `text NOT NULL` | |

Constraint: `UNIQUE (job_id, scene_id, kind)`.

---

## 6. Orchestrator state machine (M1 stub)

`run_video(ctx, job_id: int)` in `app/workers/orchestrator.py`:

```
1. Open async session.
2. job = job_repo.get(job_id); if not found, warn and return.
3. If job.status == 'cancelled': return.
4. transition(job, 'scripting')
5. await asyncio.sleep(2)                       # stub for LLM
6. scene_repo.bulk_insert_stubs(job_id, n=3)    # 3 placeholder scenes
7. transition(job, 'script_ready')
8. transition(job, 'rendering')
9. for scene in scenes_ordered:
     if job_repo.is_cancelled(job_id): return    # checkpoint
     transition_scene(scene, 'rendering')
     await asyncio.sleep(1)
     transition_scene(scene, 'done')
     progress_update(job, current_scene=scene.index+1, total=N, stage='stub_render')
10. transition(job, 'composing')
11. await asyncio.sleep(1)                      # stub for ffmpeg
12. transition(job, 'done')
```

### Allowed transitions

A single `transition()` helper validates edges against this table and raises `IllegalStateTransition` on a bad edge. Centralizing the table avoids scattered state-machine logic.

| From | Allowed → |
|---|---|
| `queued` | `scripting`, `cancelled` |
| `scripting` | `script_ready`, `failed`, `cancelled` |
| `script_ready` | `rendering`, `cancelled` |
| `rendering` | `composing`, `failed`, `partially_failed`, `cancelled` |
| `composing` | `done`, `failed`, `cancelled` |
| `done`, `failed`, `cancelled`, `partially_failed` | (terminal) |

Each transition emits `structlog.info("job.transition", job_id=..., from=..., to=...)` and updates `updated_at`.

### Cancellation

Checkpoints at steps 3, 9, and before every transition. M1 sleeps are short (≤2s), so the user observes `cancelled` within ~1s of `DELETE`. No SIGTERM in M1 — that lands in M4 when Docker containers exist.

### Idempotency

No deterministic UUIDs in M1. If Arq re-delivers `run_video(job_id)` after a crash, the worker reads `job.status` at the start. If `status='done'` it returns immediately; otherwise it advances from the current state through the allowed transitions. This is the only idempotency the M1 stub needs.

---

## 7. API surface

All routes under `/api`. Auth: `Authorization: Bearer <APP_SHARED_SECRET>`. Missing/invalid → `401` with no detail. `/healthz` and `/readyz` are unauthenticated.

### `POST /api/videos` — create job

Request body:

```json
{
  "prompt": "Explain merge sort in 60 seconds",
  "renderer": "manim",
  "duration_target": 60,
  "voice": "alloy"
}
```

Validation: `prompt` non-empty, ≤ 2000 chars; `renderer ∈ {manim, ai_image}`; `duration_target ∈ {30, 60, 180}`; `voice` non-empty.

Behavior:
1. Insert `jobs` row with `status='queued'`.
2. `arq.enqueue_job('run_video', job.id)`, persist returned id as `arq_job_id`.
3. Respond `202 Accepted` + `JobResponse`.

No idempotency-key handling in M1; calling twice yields two jobs.

### `GET /api/videos/{id}` — snapshot

Returns the full `JobResponse` with nested ordered scenes. `404` if not found. No pagination (≤ ~20 scenes per job).

### `DELETE /api/videos/{id}` — cancel

- `status ∈ {done, failed, cancelled}` → `409 Conflict`.
- Otherwise set `status='cancelled'`, respond `200` + `JobResponse`. Worker observes at the next checkpoint.

### `GET /healthz` / `GET /readyz`

Liveness/readiness. `/readyz` pings Postgres + Redis and returns `503` if either is down (drives the no-fallback policy on enqueue).

### `JobResponse` shape

```json
{
  "id": 42,
  "user_prompt": "...",
  "renderer": "manim",
  "voice": "alloy",
  "duration_target_seconds": 60,
  "status": "rendering",
  "progress": {"current_scene": 3, "total": 6, "stage": "scene_render"},
  "output_url": null,
  "cost_usd": "0.0000",
  "error": null,
  "scenes": [
    {"id": 101, "index": 0, "narration": "...", "duration_seconds": 10.5, "status": "done", "output_url": null}
  ],
  "created_at": "2026-05-19T18:00:00Z",
  "updated_at": "2026-05-19T18:01:32Z"
}
```

---

## 8. Error handling

Per CLAUDE.md "throw error where there is, no unnecessary fallbacks":

- Postgres unreachable → exception bubbles. Arq retries the worker job up to `max_tries=2`.
- Redis unreachable → `/readyz` returns `503`; `POST /api/videos` also returns `503` rather than inserting a row that can't be enqueued. No in-memory queue fallback.
- Auth failure → `401`, no leaked reason.
- Validation failure → `422` (default Pydantic).
- Unhandled exception in worker → Arq logs and re-enqueues; on final failure, `status='failed'` and `error` populated with `{type, message, trace, attempt}`.
- `transition()` helper raises `IllegalStateTransition` on a disallowed edge — surfaces a programming error rather than silently corrupting state.
- No `try/except` that swallows. No bespoke retry-with-backoff sprinkled in code. Arq owns infra-level retries.

---

## 9. Dependencies & runtime

Python 3.12.

### Core

| Package | Pin | Why |
|---|---|---|
| `fastapi` | `>=0.115,<0.116` | API tier |
| `uvicorn[standard]` | `>=0.32` | ASGI server |
| `pydantic` | `>=2.9` | |
| `pydantic-settings` | `>=2.6` | `.env` |
| `pydantic-ai` | `>=0.0.14` | placeholder import in M1, used M2 |
| `sqlalchemy[asyncio]` | `>=2.0.36` | ORM |
| `asyncpg` | `>=0.30` | async PG driver |
| `alembic` | `>=1.13` | migrations |
| `arq` | `>=0.26` | queue |
| `redis` | `>=5.2` | pinned explicitly |
| `structlog` | `>=24.4` | logging |
| `httpx` | `>=0.27` | clients + ASGI test transport |

### Dev / test

`pytest`, `pytest-asyncio`, `pytest-cov`, `testcontainers[postgres,redis]`, `ruff`, `mypy`.

### Package manager

`uv` (fast, modern). `uv.lock` checked in.

### Local runtime

- `docker-compose.yml`: `postgres:16` + `redis:7-alpine` with named volumes. Exposed on `5432` / `6379`. App is not in compose for M1 — `uvicorn` and `arq` run directly from the venv during dev. `Dockerfile` exists for CI/prod parity.
- Two foreground processes:
  - `uv run uvicorn app.main:app --reload --port 8000`
  - `uv run arq app.workers.arq_settings.WorkerSettings`
- `Makefile` targets: `dev`, `worker`, `migrate`, `test`, `fmt`, `up` (docker-compose up), `down`.

### `.env.example`

```
APP_ENV=local
APP_SHARED_SECRET=<bearer-token>
DATABASE_URL=postgresql+asyncpg://algo:algo@localhost:5432/algoreel
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO

# Unused in M1 — present so .env documents the full future surface
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=
```

---

## 10. Testing strategy

- **Unit:** `repositories/`, `services/`, the `transition()` state-machine helper. Fast, against a transactional rollback fixture.
- **Integration:** real Postgres + Redis via `testcontainers`. Covers:
  - `POST /api/videos` → row in DB and Arq job enqueued (verified via Redis client).
  - Worker stub walks job to `done` and writes 3 scenes.
  - `DELETE` mid-flight → worker stops at next checkpoint; status reflects `cancelled`.
  - Bearer-token auth: `401` on missing/wrong; `200` on valid.
  - `/readyz` returns `503` when Postgres is paused.
- **No mocked DB.** Mocks hide migration breakage.
- Coverage target: ≥ 80% on `app/` excluding `main.py` boot; enforced via `pytest --cov-fail-under=80`.

---

## 11. Future scope (deferred from M1)

Documenting what's not in M1 so M2+ planning starts from a known baseline. Order is suggested but not binding.

### M2 — LLM script generation

- Replace the `asyncio.sleep(2)` in step 5 with a PydanticAI agent call that produces a `VideoScript`.
- Two-pass LLM strategy per TRD §5.2 (cheap model for plan, Claude Sonnet for Manim code). Cost tracked in `jobs.cost_usd`.
- Persist `VideoScript` to `jobs.script` JSONB; populate real `scenes` rows from it.
- `GET /api/videos/{id}/events` (SSE) endpoint with per-stage progress events. Redis pub/sub channel per `job_id`.
- Add `Idempotency-Key` header support on `POST /api/videos` if duplicate-job pain emerges.
- Cost circuit breaker (TRD §4.5): estimate cost from script before fan-out; fail-fast over budget cap.

### M3 — TTS + object storage

- OpenAI `gpt-4o-mini-tts` per scene; ElevenLabs gated by per-job flag.
- "Audio first, then animation" — derive `scenes.duration_seconds` from TTS output.
- MinIO locally (added to `docker-compose.yml`), Cloudflare R2 in prod. Workers write audio to object storage; `assets` rows populated.
- Signed-URL helper.

### M4 — Manim renderer + render pool

- Second Arq worker on `render_pool` queue (concurrency 1 per process, `N = cpu_cores - 1`).
- Manim Community Edition + `manim-voiceover` inside a per-scene Docker container (`--read-only`, `--network=none`, CPU/mem/PID limits).
- Content-retry loop (TRD §4.4): on Manim failure capture stderr, feed back to LLM with failing code, regenerate. Cap 3 attempts per scene. `renders` audit rows populated.
- FFmpeg concat in orchestrator; final MP4 to object storage; `assets.kind='final_mp4'`.
- `POST /api/videos/{id}/resume` endpoint for `partially_failed` jobs (re-enqueue only failed scenes).
- Backpressure: `429 Too Many Requests` + `Retry-After` when `render_pool` queue depth > 50.

### M5 — Observability

- OpenTelemetry tracing: spans for `script_gen`, `tts_per_scene`, `render_per_scene`, `compose`. One trace per `job_id`.
- Prometheus metrics per TRD §8: `video_render_duration_seconds`, `llm_tokens_total`, `scene_render_attempts`, `job_cost_usd`, `queue_depth`.
- Loki for logs (already structlog-formatted).
- Grafana dashboards: failure-by-error-type, queue depth, cost-per-job, scene-retry distribution.
- Dead letter queue: `failed_jobs` list with full context (prompt, script, trace, attempts, cost) — input for prompt-engineering iteration.

### Beyond v1

- AI-image renderer (Flux Schnell via Replicate + FFmpeg Ken Burns) — TRD v1.1.
- `GET /api/videos/{id}/script` inspect/edit endpoint — TRD v1.1.
- `render_pool_interactive` priority queue for the "preview a single scene" workflow — TRD §4.7.
- Per-user fairness (Redis sorted set keyed by `user_id`) — TRD §4.7, retrofittable.
- Cross-region scheduling, burst capacity (Modal/RunPod, K8s+KEDA, Cloudflare Queues, Temporal) — TRD §4.9.
- LLM output caching by prompt hash — TRD §12 Q3.
- Script approval gating (human-in-the-loop) — TRD §12 Q1.
- Frontend (Next.js CSR per CLAUDE.md, or React+Vite per TRD §5.6 — resolve when frontend work starts).

---

## 12. Open questions

None blocking M1 implementation. The TRD's open questions (script approval gating, self-host vs Replicate, LLM output caching) all map to M2+ milestones above.

---

## 13. Risks (M1-specific)

- **`testcontainers` startup cost in CI.** First test run pulls images. Mitigate by caching Docker layers in CI; acceptable cost given the "no DB mocks" rule.
- **Arq worker crash mid-stub does not surface to API.** The job stays in whatever status it was last persisted in until Arq re-delivers. M1 accepts this — re-delivery + `max_tries=2` covers transient failures; permanent failures land `status='failed'` after retries exhaust.
- **`progress` JSONB has no schema enforcement.** Acceptable in M1; we'll lock the shape in M2 via a Pydantic model serialized on write if drift becomes a problem.
