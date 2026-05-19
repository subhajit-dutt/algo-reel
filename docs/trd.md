# Technical Requirements Document: LLM-Based Illustrative Video Generator

**Status:** Draft v0.1
**Owner:** Subhajit Dutta
**Last updated:** 2026-05-19

---

## 1. Overview

A tool that turns a text prompt into a short (≤3 min) illustrative video. The LLM generates the narrative script and per-scene assets; a renderer composes the final MP4. Two renderer paths are supported behind a common interface: **Manim** (code-driven, 3Blue1Brown-style) for v1, and **AI-image** (Flux/SDXL stills + Ken Burns motion) as a pluggable second style.

**Users:** Small internal group (~5–20). Not a public SaaS in v1.
**Non-goals:** Sora/Veo/Runway-style motion video, live editing UI, multi-language voiceover, user accounts beyond basic auth.

---

## 2. Goals & Success Criteria

| Goal | Metric | Target |
|---|---|---|
| End-to-end generation works | Job success rate (first attempt) | ≥ 70% |
| Cost per video | LLM + TTS + compute | < $1 for 3 min |
| Render latency | p50 end-to-end (3-min video) | < 12 min |
| Two renderer styles | Manim live in v1, AI-image as v1.1 | Pluggable via interface |
| Observability | Per-stage timing visible in Grafana | Day-one requirement |

---

## 3. Architecture

```
┌──────────────┐     ┌──────────────┐     ┌────────────────────┐
│ React (Vite) │────▶│ FastAPI      │────▶│ Arq job queue      │
│ + TanStack   │◀────│ (REST + SSE) │◀────│ (Redis)            │
└──────────────┘     └──────────────┘     └─────────┬──────────┘
                                                    │
                          ┌─────────────────────────┴─────────────────────────┐
                          │                                                   │
              ┌───────────▼────────────┐                       ┌──────────────▼─────────────┐
              │ Orchestrator pool      │                       │ Render pool                │
              │ (I/O-bound, asyncio)   │                       │ (CPU-bound, 1 job/worker)  │
              │                        │ enqueues scene jobs   │                            │
              │  - Script gen (LLM)    │──────────────────────▶│  - TTS per scene           │
              │  - Fan-out scenes      │                       │  - Renderer (sandboxed)    │
              │  - Await results       │◀──────────────────────│    ├─ Manim (Docker)       │
              │  - FFmpeg concat       │      scene results    │    └─ AI-image (Flux+FFmpeg)│
              │                        │                       │  - Content retry loop      │
              └───────────┬────────────┘                       └──────────────┬─────────────┘
                          │                                                   │
                          └─────────────────────┬─────────────────────────────┘
                                                │
                                      ┌─────────▼──────────┐
                                      │ Object storage     │
                                      │ (MinIO/R2)         │
                                      └────────────────────┘

                Postgres: jobs, scenes, renders (audit), assets
                Redis:    queue + SSE pub/sub
```

**Why this shape:** Video generation is inherently long-running (5–15 min). Synchronous request-response is a non-starter. The job queue + worker pool also lets us scale renderers independently of the API tier, and the renderer interface keeps Manim and AI-image paths from coupling.

---

## 4. Job Scheduling & Execution

### 4.1 The job is a DAG, not a single task

A video generation request decomposes into stages with very different resource profiles:

| Stage | Bound by | Typical duration | Parallelizable across scenes? |
|---|---|---|---|
| Script generation (LLM) | Network/API latency | 5–15s | No — one per video |
| TTS per scene | Network/API latency | 2–5s | Yes |
| Scene render (Manim or AI-image) | CPU (heavy) | 30–120s | Yes, capped by core count |
| FFmpeg concat | Disk I/O | 5–10s | No |

Treating this as one monolithic task is the naive path. A failure on scene 5 destroys 8 minutes of work, scene renders can't parallelize, and retries restart from scratch. The scheduler must reflect the DAG.

### 4.2 Two-tier worker model

The system runs **two separate worker pools** with different sizing and concurrency:

**Orchestrator pool** — lightweight, I/O-bound
- One asyncio process can hold 20+ concurrent video jobs in flight.
- Responsibilities: call the LLM for script generation, fan out scene jobs to the render pool, await results, call FFmpeg concat, update job status.
- All work here is `await` on network calls. No CPU pressure.
- Sizing: 1 process per box is usually enough; scale by job concurrency, not CPU.

**Render pool** — heavyweight, CPU-bound
- One worker process = one in-flight render job. **Concurrency per worker is intentionally 1.**
- Each render job spawns a sandboxed Docker container (read-only filesystem, no network, memory/CPU/PID caps).
- Sizing: `N = cpu_cores - 1` worker processes per box.

**Why the split is non-negotiable:** mixing I/O-bound orchestration with CPU-bound rendering on a single pool forces a bad sizing tradeoff. Size for renders and you waste 90% of capacity on orchestration; size for orchestration and renders starve each other on CPU. Netflix's video encoding pipeline and Modal Labs both use this orchestrator-vs-compute split for the same reason.

### 4.3 Job lifecycle

The lifecycle has four stages, each with its own status and persistence checkpoint:

1. **Scripting.** Orchestrator picks up the job, calls the LLM, persists the resulting `VideoScript` (with all scenes) to Postgres. Status: `scripting → script_ready`.
2. **Fan-out.** Orchestrator enqueues one render job per scene onto the render pool. Each scene job is independent and addressable by `scene_id`. Status: `rendering`.
3. **Per-scene execution.** Render worker generates TTS, then renders the scene with retries (see §4.5), uploads the scene MP4 to object storage, marks the scene `done`.
4. **Composition.** Once all scenes report `done`, orchestrator runs FFmpeg concat, uploads the final MP4, marks the job `done`. Status: `composing → done`.

Every status transition is written to Postgres before progressing. This is what makes resume possible.

### 4.4 Two layers of retry

Retries are deliberately split into two distinct mechanisms because they handle different failure classes — conflating them is a common bug.

**Infrastructure retry (queue-level).** Handled by Arq's built-in `max_tries`. Triggers on transient infra failures: worker crash, Redis hiccup, network blip, OOM kill. The whole job (orchestrator or scene) is re-enqueued and starts over. Cap at 2 attempts.

**Content retry (in-job loop).** Handled inside the render job itself. Triggers on LLM-content failures: Manim syntax error, undefined symbol, render timeout from bad geometry. The render worker captures stderr, feeds it back to the LLM with the failing code, gets new code, retries inside the same job. Cap at 3 attempts per scene.

**Why content retry stays inside the job:** re-enqueueing on a content failure loses the warm Docker container, the generated audio file, and the partial state. Retrying inside the job is faster and the worker is already provisioned correctly. The one exception is when the failure is environmental (OOM, disk full) — that gets bubbled up to the infra retry layer to land the job on a different worker.

### 4.5 Failure handling and partial result preservation

Several mechanisms work together to make failures recoverable:

- **Idempotency.** Every job and every scene has a deterministic UUID. Re-execution checks `if scene.status == 'done'` before re-rendering. Same pattern as Stripe's idempotency keys — safe to retry without producing duplicate work.
- **Scene-level persistence.** Each successful scene MP4 is uploaded to object storage and recorded in the `scenes` table before the orchestrator moves on. Scenes 1–4 succeeding then scene 5 failing leaves 4 reusable artifacts on disk.
- **Timeouts at every layer.** Arq job timeout, Docker container timeout, FFmpeg timeout, asyncio `wait_for` on LLM calls. Without these, one stuck scene halts a worker indefinitely.
- **Dead letter queue.** Jobs that exhaust both retry layers move to a `failed_jobs` list with full context: original prompt, generated script, error trace, attempt count, cost incurred. This is the input for LLM prompt improvements.
- **Cost circuit breaker.** Before fan-out, the orchestrator estimates cost from the script (token count × scene count × per-scene estimate). If the estimate exceeds the per-job budget cap, the job fails fast with a clear error. Prevents runaway LLM output (e.g., a 50-scene script) from blowing the budget.

### 4.6 Resume semantics

A job can be resumed in three scenarios:

1. **Orchestrator crash mid-job.** Arq re-delivers the orchestrator job to another worker. The new orchestrator reads the job's current status and the `scenes` table, skips work that's already done (scripting complete? skip. scenes 1–3 done? only enqueue 4–N), and continues from the first incomplete stage. No code-level checkpointing is needed because the database is the source of truth.
2. **Single scene fails after content retries.** The orchestrator marks the job `partially_failed` and exposes a `POST /api/videos/{id}/resume` endpoint that re-enqueues only the failed scenes. Successful scenes are not re-rendered.
3. **User-initiated cancellation.** Setting the job status to `cancelled` causes orchestrators and render workers to abort at the next checkpoint. In-flight Docker containers are killed via SIGTERM. Already-rendered scenes are retained for 24 hours in case the user wants to resume.

**What we explicitly do not do in v1:** durable execution in the Temporal sense — replaying the orchestrator's code from event history. Resume is implemented as "re-read state from DB, skip done work, continue." This is simpler and sufficient at ≤20 users. The migration trigger to Temporal is when we need cross-stage compensations or signals (e.g., "pause this job until a human approves the script").

### 4.7 Backpressure and fairness

- **Backpressure.** When `render_pool` queue depth exceeds a configured threshold (initial: 50), the API returns `429 Too Many Requests` with a `Retry-After` header derived from the estimated drain time. Prevents users from piling up jobs into a queue that takes hours to drain.
- **Per-user fairness.** Documented but **not implemented in v1**. Internal trust is sufficient at this scale. When needed, the implementation is round-robin enqueue keyed by `user_id` via a Redis sorted set. Retrofitting is straightforward because all jobs already carry `user_id`.
- **Priority queues.** A second `render_pool_interactive` queue is reserved for the "preview a single scene" workflow added in v1.1. Interactive jobs jump ahead of batch jobs.

### 4.8 Scheduling-specific observability

Beyond the general observability in §8, the scheduler emits:

- Queue depth per pool (sampled every 10s, drives backpressure and capacity planning)
- Job enqueue/dequeue counts by status
- Worker utilization per pool (active jobs / max jobs)
- Scene retry distribution (how many scenes succeed on attempt 1, 2, 3, or fail) — drives LLM prompt engineering investment
- Dead letter queue depth — should be near zero; spikes indicate a regression in LLM output quality
- Trace propagation: a single OTel trace spans script → fan-out → all scene renders → concat, with `job_id` as a stable correlation key across pools

### 4.9 Migration triggers

Document the conditions under which the scheduler architecture needs to change:

- **Durable workflow execution needed** (signals, compensations, long human-in-the-loop waits) → migrate to **Temporal**. Uber uses Temporal for video transcoding pipelines for exactly this reason.
- **Burst capacity needed beyond a single box** → render pool on **Modal Labs** or **Kubernetes + KEDA** scaling on Redis queue depth.
- **Cross-region scheduling** → **Cloudflare Queues** or **AWS SQS + EventBridge**.

For ≤20 users, Arq with one orchestrator process and 4 render workers on a single box covers the load for an estimated ~12 months.

---

## 5. Component Decisions & Rationale

### 5.1 Backend: FastAPI + Arq
- **FastAPI** for the API tier — native async, OpenAPI generation, Pydantic-first.
- **Arq** over Celery for the queue. Celery is industry standard but its operational surface (broker + result backend + beat + flower + worker config) is overkill for ≤20 users. Arq is asyncio-native, single Redis dependency, ~200 LoC to get running. **Migration trigger:** flip to Celery or Temporal if we hit multi-tenant scale or need workflow orchestration (compensations, signals, long-running waits).

### 5.2 LLM layer: Pydantic AI
- Structured output via Pydantic models — script comes back as a typed `VideoScript` with `scenes: list[Scene]`, not free-text we then regex.
- **Two-pass model strategy:**
  - **Pass 1 (script + scene plan):** Gemini 2.5 Flash or GPT-5-mini. Cheap, fast, good enough for narrative structure. ~$0.005/video.
  - **Pass 2 (Manim code per scene):** Claude Sonnet 4.6. Empirically better at Manim than other models — the gap matters because Manim is niche enough that training data quality varies. ~$0.02–0.04/video.
- **Retry loop:** Manim render fails → capture stderr + traceback → feed back to LLM with the failing code → regenerate. Cap at 3 attempts per scene. This is the single most important reliability mechanism in the system.

### 5.3 TTS: OpenAI gpt-4o-mini-tts (default), ElevenLabs (opt-in)
- OpenAI TTS: ~$0.015/min, "natural enough" voices (alloy, nova). Keeps us comfortably under budget.
- ElevenLabs: gated behind a per-job flag. At ~$0.18/1k chars, a 3-min video is ~$0.49 just for TTS — eats most of the budget. Worth it only when voice cloning or premium quality is needed.
- **Audio first, then animation:** generate TTS per scene, get exact duration, then constrain renderer to fit that duration. Eliminates sync drift.

### 5.4 Renderer interface (the abstraction that unifies both paths)

```python
class SceneRenderer(Protocol):
    async def render_scene(
        self, scene: Scene, audio_path: Path, duration: float
    ) -> Path: ...  # returns MP4 path
```

Both renderers consume the same `Scene` schema and return scene MP4s. Composition (FFmpeg concat) is renderer-agnostic.

**Manim renderer:**
- Manim Community Edition + `manim-voiceover` plugin for audio sync.
- Executes inside a Docker container per scene (`--read-only`, `--network=none`, CPU + memory limits). LLM-generated Python code never touches the host. For internal use, Docker is sufficient; gVisor/Firecracker is the upgrade path if we ever expose this externally.
- **Known limitation:** CPU-bound, 30–120s render per 30s scene at 1080p. Burst capacity via Modal Labs or RunPod when queue depth grows.

**AI-image renderer (v1.1):**
- Flux Schnell via Replicate ($0.003/image) for ~15–20 scene stills. Self-host SDXL only if we hit cost or rate-limit issues.
- FFmpeg Ken Burns (zoom/pan) per still + crossfade transitions. No frame-by-frame generation — that's the Sora path and breaks the budget.
- **Known limitation:** visual consistency across scenes (same character/style across 20 images) is the dominant quality issue. Mitigations: seed reuse, style prompts pinned in system prompt, optionally a single reference image fed via Flux's image-to-image. This is a real research problem, not a checkbox.

### 5.5 Storage: MinIO (local) / Cloudflare R2 (prod)
- Workers write MP4 + intermediate assets directly to object storage. API returns signed URLs.
- **Why R2 over S3:** zero egress fees. For video delivery this is the difference between "viable" and "expensive at any scale."
- Never proxy video bytes through FastAPI.

### 5.6 Frontend: React + Vite + TanStack Query + SSE
- Vite for build speed, TanStack Query for server state.
- **Server-Sent Events for job progress** (not polling). One endpoint, one line in FastAPI (`EventSourceResponse`), per-scene progress updates ("Rendering scene 3 of 6 — retry 1"). Materially improves perceived latency on a 10-minute job. WebSockets are overkill — traffic is server→client only.

### 5.7 Data layer: Postgres + Redis
- **Postgres:** `jobs`, `scenes`, `renders` (audit trail of attempts), `assets` (object storage pointers). Use `jsonb` for the `VideoScript` payload — schema evolves, we don't want a migration per LLM prompt change.
- **Redis:** Arq queue + SSE pub/sub channel.

---

## 6. Data Model (essentials)

```python
class Scene(BaseModel):
    id: UUID
    index: int                    # order in video
    narration: str                # spoken text
    visual_prompt: str            # renderer-agnostic description
    manim_code: str | None        # populated by Manim path
    image_prompts: list[str] | None  # populated by AI-image path
    duration_seconds: float

class VideoScript(BaseModel):
    title: str
    scenes: list[Scene]
    renderer: Literal["manim", "ai_image"]
    voice: str                    # tts voice id
    total_duration: float

class Job(BaseModel):
    id: UUID
    user_prompt: str
    status: Literal["queued", "scripting", "rendering", "composing", "done", "failed"]
    progress: dict                # {"current_scene": 3, "total": 6, "stage": "manim_render"}
    script: VideoScript | None
    output_url: str | None
    cost_usd: Decimal             # tracked per stage for budget alerting
```

---

## 7. API Surface (minimal)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/videos` | Create job; body: `{prompt, renderer, duration_target, voice}` |
| `GET` | `/api/videos/{id}` | Job status snapshot |
| `GET` | `/api/videos/{id}/events` | SSE stream of progress events |
| `GET` | `/api/videos/{id}/script` | Inspect/edit generated script before render (v1.1) |
| `DELETE` | `/api/videos/{id}` | Cancel queued job |

Auth: simple shared-secret bearer token for the internal group. Replace with OAuth/Clerk if scope grows.

---

## 8. Observability

Day-one requirements — debugging "why did this video take 18 minutes" is impossible without these:

- **Tracing:** OpenTelemetry spans around `script_gen`, `tts_per_scene`, `render_per_scene`, `compose`. One trace per job.
- **Metrics (Prometheus → Grafana):**
  - `video_render_duration_seconds` (histogram, labels: renderer, scene_count)
  - `llm_tokens_total` (counter, labels: model, pass)
  - `scene_render_attempts` (histogram — surfaces flaky LLM output)
  - `job_cost_usd` (gauge per job — alert at >$1)
  - `queue_depth` (gauge — capacity planning)
- **Logs:** structlog → stdout → Loki. Every log includes `job_id` + `scene_id`.
- **Failure dashboard:** scene render failure rate by error type (Manim syntax error vs. timeout vs. OOM vs. asset upload). This drives the LLM prompt improvements.

---

## 9. Non-Functional Requirements

| NFR | Target |
|---|---|
| Concurrent jobs | 5 (matches initial worker count) |
| Worker memory ceiling | 4 GB per Manim render |
| Job timeout | 20 min hard kill |
| Storage retention | 30 days, then lifecycle-delete |
| Secrets | env vars in dev, AWS SSM / Doppler in prod |
| Backup | Postgres daily snapshot (jobs metadata); object storage is the asset store |

---

## 10. Key Risks & Trade-offs

1. **LLM-generated Manim is unreliable (~60–70% first-try success).** Mitigated by the retry loop, but it's the dominant source of latency variance. Worth budgeting for a Manim-specific fine-tune if we ever go past internal use.
2. **3-minute videos are ambitious for Manim.** The format shines at 30–90s. At 3 min, narrative coherence drops and visual fatigue rises. **Recommendation:** ship with 30s/60s/180s tiers, default to 60s.
3. **Visual consistency on the AI-image path is unsolved.** Acknowledged limitation — don't promise character continuity in v1.1.
4. **Single-machine deployment is fine for ≤20 users but caps at queue depth ~5.** Burst to Modal/RunPod for renders when queue depth exceeds threshold. Documented but not built in v1.
5. **"Single Python project" is fine as a monorepo; the workers must run as separate processes.** Rendering Manim inside the FastAPI process will block the event loop and OOM the API. This is a hard rule.

---

## 11. Out of Scope (v1)

- Multi-user auth, billing, quotas
- Editing UI for the generated script (added v1.1)
- Multi-language TTS
- Video styles beyond Manim + AI-image
- Mobile app
- Watermarking / DRM

---

## 12. Open Questions

1. Do we need script approval gating (human-in-the-loop before render starts) for v1, or is fire-and-forget acceptable for internal use?
2. Self-host Flux/SDXL on a GPU box, or stay on Replicate for v1.1? (Lean: Replicate. Self-host only if monthly Replicate bill exceeds GPU rental.)
3. Should we cache LLM outputs by prompt hash to deduplicate repeat requests? Cheap win if it happens often, dead weight if not.