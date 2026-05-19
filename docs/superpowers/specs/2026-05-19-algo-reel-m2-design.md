# Algo-Reel Milestone 2 — LLM Script Generation + SSE Progress

**Status:** Approved (brainstorming)
**Owner:** Subhajit Dutta
**Date:** 2026-05-19
**Related:** [docs/trd.md](../../trd.md), [M1 design](2026-05-19-algo-reel-m1-design.md)

---

## 1. Purpose

Replace M1's `asyncio.sleep(2)` script-generation stub with a real LLM call that produces a typed `VideoScript`, persist that script + derived scenes, surface progress to the client via Server-Sent Events, and enforce a cost circuit breaker so a runaway script can't blow the per-job budget.

This milestone is "done" when:

- The orchestrator calls a PydanticAI agent backed by OpenRouter, gets a typed `VideoScript`, persists it to `jobs.script` JSONB, and inserts real `scenes` rows derived from it.
- `jobs.cost_usd` reflects the actual LLM spend for the script-gen call.
- A bearer-authenticated client can `GET /api/videos/{id}/events` and receive a snapshot followed by streaming progress deltas until the job hits a terminal status.
- The cost circuit breaker fails a job fast before fan-out if the script violates scene-count, duration, or per-call cost caps.
- Integration tests cover the orchestrator E2E against a `TestModel`-backed agent (no live LLM in CI).

---

## 2. Scope

### In scope

- `app/llm/` package: PydanticAI agent + pricing table.
- OpenRouter as the unified LLM gateway (single key, OpenAI-compatible base URL).
- `VideoScript` persistence on `jobs.script`; cost on `jobs.cost_usd`.
- `SceneRepo.bulk_insert_from_script` replaces `bulk_insert_stubs` in the orchestrator path.
- Cost circuit breaker (max scenes, duration drift, per-call cost cap).
- `GET /api/videos/{id}/events` SSE endpoint backed by Redis pub/sub channel `job_progress:{job_id}`.
- `ProgressPublisher` helper used by the orchestrator at every transition + per-scene update.
- Tests: unit (agent with `TestModel`, pricing, circuit breaker), integration (orchestrator E2E + SSE stream), no live LLM in CI.
- `make smoke-llm` target hits the real OpenRouter endpoint behind an env flag for manual verification.

### Out of scope (deferred)

- **Pass 2 — Manim code generation per scene.** Deferred to M4. Spec §11 puts both passes in M2, but the content-retry loop that wraps Pass 2 lives in M4 alongside the renderer; generating un-validateable code in M2 is wasted spend. M4's plan will note that Pass 2 + retry loop colocate in the render worker.
- **TTS-derived per-scene durations.** Until M3, `scenes.duration_seconds` carries the LLM-proposed value as a placeholder.
- **`Idempotency-Key` on `POST /api/videos`.** Spec language is "if duplicate-job pain emerges" — no signal yet.
- **OTel / Prometheus instrumentation** of the LLM call. M5.
- **Frontend SSE consumer.** Backend-only milestone.

---

## 3. Architecture additions

```
app/
├── llm/
│   ├── __init__.py
│   ├── script_agent.py        # PydanticAI Agent + generate_script() entry point
│   ├── pricing.py             # MODEL_PRICING table + compute_cost(model, usage)
│   └── prompts.py             # SCRIPT_SYSTEM_PROMPT constant (renderer/duration aware)
├── services/
│   └── progress_publisher.py  # publish(job_id, event) over Redis pub/sub
├── api/
│   └── sse.py                 # GET /api/videos/{id}/events
└── schemas/
    └── event.py               # ProgressEvent shape

app/repositories/scene_repo.py # + bulk_insert_from_script(job_id, script)
app/workers/orchestrator.py    # SCRIPTING step swaps sleep for agent call + publish hooks
app/main.py                    # + Redis client singleton on app.state (for SSE subscribe)
app/config.py                  # + openrouter_api_key, llm_base_url, llm_script_model, etc.
```

No new Alembic migration. M1's schema already provisions `jobs.script` JSONB and `jobs.cost_usd` numeric.

### Layering rules (additive — same as M1)

- `app/llm/` is a leaf module; it has no dependency on `repositories/`, `services/`, or `db/`.
- `services/progress_publisher.py` depends only on `redis` and `schemas/event.py`. It does not call the DB.
- `api/sse.py` calls the existing `JobService` for the snapshot read and the publisher's `subscribe()` for the live stream.
- `workers/orchestrator.py` is the only caller of `script_agent.generate_script` and the only writer to `job_repo.set_script` / `job_repo.set_cost`.

---

## 4. LLM gateway — OpenRouter

All model traffic goes through OpenRouter, not direct provider SDKs.

**Why:** one API key, one bill, one auth surface, trivial model swaps for cost/quality tuning across providers. Provider SDK divergence is real operational overhead at the scale of two LLM callsites (M2 + M4).

### Configuration

| Env var | Default | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | (required) | secret |
| `LLM_BASE_URL` | `https://openrouter.ai/api/v1` | OpenAI-compatible |
| `LLM_SCRIPT_MODEL` | `anthropic/claude-haiku-4.5` | OpenRouter slug |
| `LLM_SCRIPT_MAX_TOKENS` | `4000` | hard cap on agent output |
| `LLM_TIMEOUT_SECONDS` | `60` | per-call wall clock |
| `MAX_SCRIPT_COST_USD` | `0.10` | circuit-breaker per-call cap |
| `MAX_SCENES_PER_VIDEO` | `12` | circuit-breaker scene cap |

Removed from `.env.example`: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` — OpenRouter replaces them.

OpenRouter likes two attribution headers; we set them on the provider:

- `HTTP-Referer: https://algo-reel.local`
- `X-Title: algo-reel`

### PydanticAI wiring

```python
from openai import AsyncOpenAI
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

_client = AsyncOpenAI(
    base_url=settings.llm_base_url,
    api_key=settings.openrouter_api_key,
    default_headers={
        "HTTP-Referer": "https://algo-reel.local",
        "X-Title": "algo-reel",
    },
    timeout=settings.llm_timeout_seconds,
)
_model = OpenAIModel(settings.llm_script_model, provider=OpenAIProvider(openai_client=_client))
script_agent: Agent[None, VideoScript] = Agent(
    _model,
    output_type=VideoScript,
    system_prompt=SCRIPT_SYSTEM_PROMPT,
)
```

`VideoScript` (already defined in `app/domain/script.py`) is the structured-output type. PydanticAI enforces the schema on the model response; failures bubble as exceptions.

### Pricing & cost

`app/llm/pricing.py` holds a static table keyed by OpenRouter slug:

```python
MODEL_PRICING: dict[str, Pricing] = {
    "anthropic/claude-haiku-4.5": Pricing(input_per_mtok=Decimal("1.00"), output_per_mtok=Decimal("5.00")),
    # extend as needed
}
```

`compute_cost(model: str, usage: Usage) -> Decimal` returns `(input_tokens × in_price + output_tokens × out_price) / 1_000_000`, rounded to `Decimal(quantize="0.0001")` to match the DB column scale. Unknown model → raise (no silent zero).

Rationale for static table over OpenRouter's `/models` endpoint: deterministic, no extra round-trip per job, easy to bump in a PR. We re-sync the table when we change models.

---

## 5. Script agent contract

```python
async def generate_script(
    *,
    prompt: str,
    renderer: Renderer,
    duration_target_seconds: int,
) -> ScriptGenResult:
    """Returns (VideoScript, cost_usd). Raises on agent error, schema error, or LLM unavailability."""
```

```python
@dataclass(frozen=True)
class ScriptGenResult:
    script: VideoScript
    cost_usd: Decimal
    model: str
```

The system prompt (`SCRIPT_SYSTEM_PROMPT`) is parameterized via the agent's `user_prompt` content with `renderer` and `duration_target_seconds`:

- Asks for `title`, `scenes[index, narration, visual_prompt, duration_seconds]`, `total_duration`.
- Constrains: scene durations sum within ±20% of target; scene count between 3 and `MAX_SCENES_PER_VIDEO`; narration ≤ 300 chars/scene (TTS-friendly).
- For `renderer=manim`: visual_prompt should describe diagrammatic / mathematical content.
- For `renderer=ai_image`: visual_prompt should be a still-image description.

**No retries inside the agent.** Failures propagate to the orchestrator. Arq's `max_tries=2` covers transient infra. Content-retry (for Manim) is M4.

---

## 6. Cost circuit breaker

Applied **after** the agent returns, **before** any scene rows are inserted:

```python
def enforce_budget(script: VideoScript, cost: Decimal, *, target_seconds: int) -> None:
    if cost > settings.max_script_cost_usd:
        raise BudgetExceededError("script_cost", cost)
    if len(script.scenes) > settings.max_scenes_per_video:
        raise BudgetExceededError("scene_count", len(script.scenes))
    if not (3 <= len(script.scenes) <= settings.max_scenes_per_video):
        raise BudgetExceededError("scene_count", len(script.scenes))
    drift = abs(script.total_duration - target_seconds) / target_seconds
    if drift > 0.20:
        raise BudgetExceededError("duration_drift", drift)
```

`BudgetExceededError` carries `(reason, value)`. The orchestrator catches it, marks the job `failed` with `error={type:"budget_exceeded", reason, value}`, publishes a `failed` SSE event, and exits.

Why these caps:
- **Cost cap** protects against pricing surprises and prompt-injection-driven token blow-up.
- **Scene cap** is TRD §4.5's "50-scene runaway script" guard.
- **Duration drift** catches scripts that don't respect the requested length tier.

---

## 7. SSE — `GET /api/videos/{id}/events`

### Endpoint

- Auth: same `Bearer` header as the rest of `/api/videos`. No query-string token. SSE clients use fetch-streaming (browser `EventSource` polyfills support headers via `@microsoft/fetch-event-source` or `EventSource` v2; we don't optimize the auth model for vanilla `EventSource`).
- Behavior:
  1. Load job. If not found → `404`.
  2. Emit **snapshot** event with the full current `JobResponse`.
  3. If status is terminal → close the stream.
  4. Else subscribe to Redis channel `job_progress:{job_id}`; forward each message as an SSE event.
  5. Close on first terminal event received, or on client disconnect.
- Library: `sse-starlette`'s `EventSourceResponse` — provides heartbeats (`ping=15s`) and proper framing.

### Event shapes (`app/schemas/event.py`)

Two event types share a common base:

```python
class ProgressEvent(BaseModel):
    event: Literal["snapshot", "progress", "transition", "failed", "done"]
    job_id: int
    status: JobStatus
    progress: dict[str, Any]
    scene_id: int | None = None
    error: dict[str, Any] | None = None
    ts: datetime
```

`snapshot` is the first message and carries the same payload shape as `progress`. Clients ignore the distinction unless they want a "we've caught up" marker.

### Redis channel

- One channel per job: `job_progress:{job_id}`.
- Payload: `ProgressEvent.model_dump_json()`.
- Publisher: `ProgressPublisher.publish(job_id, event)` in the worker, called inside `_transition()` and after every per-scene progress update.
- Subscriber: created per SSE connection via `redis.pubsub()`; auto-cleanup on stream close.
- Channel name is namespaced so future channels (e.g. `cost_alert:`) don't collide.

### Redis client on app.state

`app/main.py` lifespan adds a second Redis singleton dedicated to pub/sub (separate from `app.state.arq` because Arq's `ArqRedis` is a connection pool tuned for command operations; pub/sub wants a dedicated connection per subscription).

```python
app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
```

`get_redis` dependency in `deps.py` exposes it to routes and the SSE endpoint.

### Why pub/sub instead of polling the DB

Polling at 1s intervals on a 10-minute job = 600 reads/job × concurrent SSE viewers. Pub/sub fans out a single write to N subscribers in O(1) Redis ops. SSE clients also see transitions at sub-second latency, which is the whole point of the channel.

### Reconnect semantics

- Server sends a `Last-Event-ID` on every event (the `event_id` UUID).
- On reconnect, client passes `Last-Event-ID`; server emits a fresh snapshot (cheap) and then resumes streaming. We do **not** maintain an event log; the snapshot is the catchup mechanism. Sufficient for ≤20 users.

---

## 8. Orchestrator changes

```python
SCRIPTING:
    publisher.publish(job_id, ProgressEvent(event="transition", status=SCRIPTING, ...))
    result = await script_agent.generate_script(
        prompt=job.user_prompt,
        renderer=Renderer(job.renderer),
        duration_target_seconds=job.duration_target_seconds,
    )
    enforce_budget(result.script, result.cost_usd, target_seconds=job.duration_target_seconds)
    await job_repo.set_script(job_id, result.script.model_dump(mode="json"))
    await job_repo.add_cost(job_id, result.cost_usd)
    await scene_repo.bulk_insert_from_script(job_id, result.script)
    transition → SCRIPT_READY
```

Per-scene loop in `RENDERING` keeps M1's stub behavior (sleep + status flip), but now publishes after each scene's progress update.

`JobRepo` gains:
- `set_script(job_id: int, script: dict) -> None`
- `add_cost(job_id: int, cost: Decimal) -> None`  (additive, so M4's render cost lands cumulatively)

`SceneRepo` gains:
- `bulk_insert_from_script(job_id: int, script: VideoScript) -> list[Scene]` — replaces `bulk_insert_stubs` in the orchestrator path. The stubs helper stays for unit tests that need a quick seed.

### Cancellation

No change. Existing checkpoints fire before/after the LLM call by virtue of `_assert_not_terminal()` at scene-loop entry and the `_transition()` conditional UPDATE.

If `DELETE /api/videos/{id}` lands mid-LLM-call, the call completes (we don't have OpenRouter request cancellation in v1) but the next `_transition()` becomes a no-op because the row is already `cancelled`. Cost still gets recorded if we got that far — acceptable; documented in §13.

---

## 9. Error handling (per CLAUDE.md — no fallbacks)

| Failure | Behavior |
|---|---|
| OpenRouter network error | `RuntimeError` bubbles → orchestrator sets `status='failed'`, error payload `{type, message}`, publishes `failed` event. Arq retries up to `max_tries=2`. |
| LLM output fails Pydantic validation | PydanticAI raises `ModelRetry` or `UnexpectedModelBehavior`; same path as above. |
| `BudgetExceededError` | `status='failed'`, error `{type:"budget_exceeded", reason, value}`. **No retry** — re-running won't change the structural problem. We mark `attempts` so this shows up in M5 dashboards. |
| Unknown model in pricing table | `RuntimeError` at agent boot (sanity check at config load). Catches the misconfigured-deploy case. |
| SSE client disconnect | Server-side stream closes; Redis subscription cleaned up. No log spam. |

No `try/except` that swallows. No bespoke retry-with-backoff. Arq owns infra-level retries.

---

## 10. Testing strategy

- **No live LLM in CI.** All agent tests use PydanticAI's `TestModel` (`pydantic_ai.models.test.TestModel`), which returns a fixture `VideoScript` deterministically. Inject via `Agent.override(model=TestModel(...))` in tests.
- **Unit:**
  - `pricing.compute_cost` — table-driven, including unknown-model raise.
  - `enforce_budget` — one test per circuit-breaker branch + a happy-path test.
  - `bulk_insert_from_script` — verifies scene count, index ordering, narration/visual_prompt persistence.
  - `ProgressPublisher.publish/subscribe` round-trip via `fakeredis` or the testcontainer Redis.
- **Integration:**
  - Orchestrator E2E with `TestModel` plumbed in. Asserts `jobs.script` populated, `cost_usd > 0`, `scenes` rows match the test script.
  - Orchestrator failure path: `TestModel` returns a script that violates `MAX_SCENES_PER_VIDEO`; asserts `status='failed'` and error blob shape.
  - SSE: `httpx.AsyncClient` `.stream("GET", url)`, run the worker in-process, assert event sequence (`snapshot → transition(scripting) → transition(script_ready) → transition(rendering) → progress×3 → transition(composing) → transition(done)`).
- **Manual smoke:** `make smoke-llm` posts a real job, lets the worker hit OpenRouter, verifies a non-stub `VideoScript` lands in DB. Behind `ALGOREEL_ALLOW_LIVE_LLM=1` env flag.
- **Coverage target:** keep ≥ 80% on `app/`; new packages held to the same bar.

---

## 11. Dependencies & runtime additions

| Package | Pin | Why |
|---|---|---|
| `openai` | `>=1.50` | client used by PydanticAI's `OpenAIProvider` against OpenRouter |
| `sse-starlette` | `>=2.1` | `EventSourceResponse` with heartbeats |

`pydantic-ai>=0.0.14` already pinned in M1 — bump if needed during implementation.

No new infra (still Postgres + Redis). No new Docker services.

Process topology unchanged: `uvicorn` + `arq` (orchestrator queue). Render pool still M4.

---

## 12. Updated `.env.example`

```
APP_ENV=local
APP_SHARED_SECRET=change-me-in-real-env
DATABASE_URL=postgresql+asyncpg://algo:algo@localhost:5432/algoreel
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO

# LLM gateway (OpenRouter, OpenAI-compatible)
OPENROUTER_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_SCRIPT_MODEL=anthropic/claude-haiku-4.5
LLM_SCRIPT_MAX_TOKENS=4000
LLM_TIMEOUT_SECONDS=60
MAX_SCRIPT_COST_USD=0.10
MAX_SCENES_PER_VIDEO=12

# Unused until M3 — kept so .env documents the future surface
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=
```

`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` removed.

---

## 13. Risks & trade-offs (M2-specific)

- **OpenRouter is a single point of failure for LLM traffic.** Acceptable at ≤20 users; migration trigger is to add a second provider behind the same `OpenAIProvider` interface and a config-level model fallback. Not built in M2.
- **Mid-call cancellation costs money.** A `DELETE` during the LLM call doesn't abort the OpenRouter request; we still pay for tokens generated. Documented; acceptable at this scale.
- **Schema drift in `VideoScript`.** Once `jobs.script` is populated with v1 shape, a future Pydantic-model change needs either a migration step or a `version` field on the JSONB. Add `script_version: int` to `VideoScript` at the model layer to give us an evolution lever for free.
- **`TestModel` deterministic but blind to schema mistakes.** A `TestModel` happy path won't catch a malformed system prompt that the real model would mishandle. Mitigation: `make smoke-llm` in PR review for any prompt change.
- **SSE behind reverse proxies.** Nginx/Cloudflare default-buffer SSE. Document the `X-Accel-Buffering: no` header (we already set it via `sse-starlette`) and proxy config in the deploy guide when prod lands.
- **`MAX_SCENES_PER_VIDEO=12` is a guess.** TRD §4.5 mentions 50 as a clear runaway; 12 is "what fits comfortably in a 3-min video at 15s/scene avg." Tunable.

---

## 14. Future scope (deferred from M2)

- **Pass 2 — Manim code per scene + content-retry loop** → M4.
- **Idempotency-Key header** on `POST /api/videos` if duplicate-job pain appears.
- **`GET /api/videos/{id}/script` inspect/edit endpoint** → TRD v1.1.
- **LLM output caching by prompt hash** → TRD §12 Q3, evaluate after we have real usage data.
- **Provider fallback / multi-model router** → migration trigger above.
- **OTel spans around `script_gen`** → M5.

---

## 15. Open questions

None blocking M2 implementation.

---

## 16. Self-review notes

- All requirements in §11 of the M1 design map to in-scope (LLM script gen, persistence, cost, SSE, circuit breaker) or explicitly-deferred (Pass 2 Manim, idempotency-key) items. No silent gaps.
- No `TBD` / `TODO` placeholders.
- Naming consistent across sections: `script_agent`, `ProgressPublisher`, `enforce_budget`, `bulk_insert_from_script`, `job_progress:{job_id}`, `OPENROUTER_API_KEY`, `LLM_SCRIPT_MODEL`.
- Single implementation plan can cover the whole milestone; no decomposition required.
- Deviation from spec §11 (Pass 2 deferred to M4) called out in §2 and §14.
