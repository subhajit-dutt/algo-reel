# Algo-Reel Milestone 4 — Render Pool + Sandboxed Trivial Renderer + Composition

**Status:** Approved (brainstorming)
**Owner:** Subhajit Dutta
**Date:** 2026-06-09
**Related:** [docs/trd.md](../../trd.md), [M1 design](2026-05-19-algo-reel-m1-design.md), [M2 design](2026-05-19-algo-reel-m2-design.md), [M3 design](2026-06-07-algo-reel-m3-design.md)

---

## 1. Purpose

Produce a real, playable MP4 end-to-end. Today the pipeline is real through TTS (M3) and then fakes the rest: the `RENDERING` block sleeps and marks scenes `done` with `stage="stub_render"`, and `COMPOSING` sleeps and marks the job `done` — no renderer, no FFmpeg, `output_url` never written ([orchestrator.py:144-176](../../../app/workers/orchestrator.py)).

M4 replaces both stubs with the real two-pool execution architecture from TRD §4.2 — but deliberately pairs it with a **trivial renderer** so the milestone proves the *plumbing* (process split, sandbox harness, fan-out/await, composition, asset persistence) without simultaneously fighting Manim's ~60–70% first-try failure rate (TRD Risk #1). Manim is a drop-in behind the same `SceneRenderer` Protocol in M5.

The single most important design property: **the trusted/untrusted boundary is the command that runs inside the sandbox, not the harness around it.** M4 exercises the full container lock-down (read-only fs, `--network=none`, CPU/mem/PID caps, non-root, timeout/kill, stderr capture) on a *trusted* FFmpeg command. M5's `ManimRenderer` reuses that exact harness to run *untrusted* LLM-generated code.

This milestone is "done" when:

- After `SCRIPT_READY` voicing, the orchestrator fans out one `render_scene` job per scene onto a **separate `render_pool` Arq queue** (concurrency 1), awaits all results, then enqueues one `compose_video` job and awaits it — all via `await`-on-result, no CPU/subprocess work in the orchestrator process.
- Each `render_scene` job runs the trivial renderer **inside a sandboxed Docker container**, uploads the scene MP4 (`AssetKind.SCENE_MP4`), sets `scenes.output_url` + status `done`, and writes a `renders` audit row.
- `compose_video` FFmpeg-concats the scene MP4s into a final MP4, uploads it (`AssetKind.FINAL_MP4`), and sets `jobs.output_url`.
- A job reaching `done` has a non-null `jobs.output_url` pointing at a playable MP4 whose audio is the synthesized narration, length-matched per scene.
- Re-delivery (Arq `max_tries`) and orchestrator restart skip already-`done` scenes and an already-composed job (idempotent), re-running only the incomplete work.
- Unit/integration tests cover the orchestrator → render → compose path with a **faked sandbox runner** — no real Docker, no nested `docker run` in CI. `make smoke-render` builds the image and renders a real MP4 behind an env flag.

---

## 2. Scope

### In scope

- `app/render/` package (leaf, db-free — imports only stdlib + `app.config` + `app.domain`, mirroring `app/tts` and `app/storage`):
  - `sandbox.py` — `run_sandboxed(...)` docker-exec primitive + `get_sandbox_runner()` injection seam.
  - `base.py` — `SceneRenderer` Protocol, `RenderError`, `get_renderer()`.
  - `trivial.py` — `TrivialRenderer` (FFmpeg static card sized to the scene's audio duration).
- `docker/render/Dockerfile` — one pinned `algoreel-render` image (ffmpeg + bundled font + non-root user). M5 adds Manim to the same image.
- `app/workers/render.py` — the `render_scene(ctx, scene_id)` and `compose_video(ctx, job_id)` Arq job functions (wire `app/render` → storage → repos).
- `RenderRepo` (`app/repositories/render_repo.py`) — first writes to the `renders` audit table (`start_attempt`, `mark_succeeded`, `mark_failed`).
- `SceneRepo.set_output_url(...)` and a `set_status` that already exists (`update_status`) — populate `scenes.output_url`.
- `JobRepo.set_output_url(...)` — populate `jobs.output_url` at compose.
- `Storage.get(key) -> bytes` added to the `Storage` Protocol + `LocalStorage` — the read path the render/compose pools use to materialize the audio and scene MP4s into the container input mount (M3 only needed `put`/`url`). Backend-agnostic so it survives the R2 swap.
- Orchestrator rewiring: `RENDERING` block fans out + awaits real render jobs; `COMPOSING` block enqueues + awaits the compose job. A render-queue Arq pool (`create_pool`) is opened for enqueue/await.
- A second Arq worker entrypoint `RenderWorkerSettings` (queue `render_pool`, `max_jobs=1`).
- `progress` SSE events with `stage="render"` (per scene) and `stage="compose"` (reuses the M2 `ProgressPublisher`; no SSE contract change).
- Config: `render_*` settings (image, queue, caps, timeout, video size/fps, non-root user).
- Tests: unit (sandbox flag construction, trivial-renderer command/staging, `render_scene`/`compose_video` job logic with a faked runner, orchestrator E2E to `DONE` with `output_url` set, scene-render-failure path) + `make smoke-render` behind `ALGOREEL_ALLOW_LIVE_RENDER=1`.
- Docs: `docs/apis/videos.md` (`stage` values `render`/`compose`; `output_url` now populated on `done`), `.env.example`, `Makefile` (`render-image`, `render-worker`), README quick-start (two worker processes now).

### Out of scope (deferred)

- **Manim renderer + Pass-2 LLM Manim code-generation** (populating `scenes.manim_code`). M5. The `SceneRenderer` Protocol is the seam.
- **Pass-2 pre-render critic + heterogeneous Sonnet→Opus retry + the in-job content-retry loop** (TRD §4.4, §5.2). These exist to handle *content* failures from generated code; there is no generated code in M4. M5.
- **`partially_failed` + `POST /api/videos/{id}/resume`.** Per-scene partial failure only earns its keep once content failures are an expected class (Manim, M5). In M4 a scene render failure fails the whole job (see §8). The `partially_failed` status already exists in the enum/state machine, so this is purely additive later.
- **Container-kill-on-cancel (SIGTERM to in-flight containers).** TRD §4.6. Trivial renders are sub-second, bounded by `render_timeout_seconds` + Arq `job_timeout`. Becomes real with Manim's 30–120s renders. M5.
- **Render-cost circuit breaker** (pre-fan-out estimate, TRD §4.5). Trivial-renderer compute cost is $0. M5.
- **Object storage (R2) + signed URLs.** Still `LocalStorage` under `MEDIA_ROOT`, shared between the two pools as a filesystem (see §3 note). The migration trigger is unchanged from M3 §13.
- **OTel / Prometheus** instrumentation of the render/compose stages. M5.
- **AI-image renderer** (TRD §5.4). v1.1.
- Unrelated: the Pass-1 model is still `anthropic/claude-haiku-4.5` ([config.py:22](../../../app/config.py)) vs TRD v0.3 §5.2's Sonnet 4.6. Noted, not M4.

---

## 3. Architecture additions

```
app/
├── render/                      # NEW leaf package (db-free, like app/tts, app/storage)
│   ├── __init__.py
│   ├── sandbox.py               # run_sandboxed(...) + SandboxLimits + RunResult + get_sandbox_runner()
│   ├── base.py                  # SceneRenderer Protocol + RenderError + RenderInput + get_renderer()
│   └── trivial.py               # TrivialRenderer (ffmpeg card)
├── workers/
│   ├── render.py                # NEW — render_scene(ctx, scene_id), compose_video(ctx, job_id) Arq jobs
│   ├── arq_settings.py          # + RenderWorkerSettings; + render-queue pool helper
│   └── orchestrator.py          # RENDERING + COMPOSING blocks rewired (stubs removed)
├── repositories/
│   ├── render_repo.py           # NEW — RenderRepo (renders audit writes)
│   ├── scene_repo.py            # + set_output_url(...)
│   └── job_repo.py              # + set_output_url(...)
└── storage/
    ├── base.py                  # + Storage.get(key) -> bytes
    └── local.py                 # + LocalStorage.get (read_bytes)

docker/render/Dockerfile         # NEW — algoreel-render image (ffmpeg + font + nonroot)
```

**Two-pool topology and data flow:**

```
orchestrator_pool (existing queue)              render_pool (NEW queue, max_jobs=1, N=cores-1 procs)
────────────────────────────────────           ──────────────────────────────────────────────────
run_video(job_id):                              render_scene(scene_id):
  scripting (LLM, M2)                             skip if scene.status == done            (idempotent)
  tts        (M3)                                 stage audio.wav + text.txt into /in
  RENDERING:                                      renders row: start (attempt=1)
    for each not-done scene:                      run_sandboxed(trivial card) -> /out/scene.mp4
      enqueue render_scene -> render_pool         upload SCENE_MP4; scene.output_url + done
    await all results (asyncio.gather)            renders row: succeeded(duration_ms)  | failed(stderr)
  COMPOSING:                                    compose_video(job_id):
    enqueue compose_video -> render_pool          skip if job.output_url set            (idempotent)
    await result                                  run_sandboxed(ffmpeg concat) -> final.mp4
  done                                            upload FINAL_MP4; job.output_url
```

The orchestrator pool stays **pure async-IO** — it only `enqueue`s and `await`s results. All ffmpeg/docker execution lives in the render pool. This honors TRD §4.2's rule that the orchestrator does *"`await` on network calls. No CPU pressure."*

**Deliberate deviation from TRD §4.3.** §4.3 step 4 says the *orchestrator* runs FFmpeg concat. That contradicts §4.2 (no CPU/subprocess pressure in the orchestrator) and would force ffmpeg into the orchestrator's runtime image. M4 resolves the inconsistency by making composition a `compose_video` render-pool job. Composition operates on our own trusted scene MP4s, so it is *not* security-sensitive — it reuses the same `run_sandboxed` harness only to keep all ffmpeg execution off the orchestrator process. Cost: one extra enqueue+await hop per job.

**No new Alembic migration.** [0001_init](../../../alembic/versions/0001_init.py) already provisions: `scenes.output_url` (Text, nullable), `jobs.output_url` (Text, nullable), the full `renders` table (`scene_id`, `attempt`, `status IN ('started','succeeded','failed')`, `stderr`, `duration_ms`, `cost_usd`, index `(scene_id, attempt)`), and the `assets` CHECK already lists `scene_mp4`/`final_mp4`. M4 is their first writer.

**Shared-storage prerequisite.** Both pools must see the same bytes: the render worker reads the audio the orchestrator wrote, and the compose worker reads the scene MP4s the render workers wrote. With `LocalStorage`, that means the two worker processes share the `MEDIA_ROOT` filesystem (same box / shared volume — fine for the documented single-box v1). The object-storage migration removes this constraint; the `Storage` interface already abstracts it.

---

## 4. The sandbox harness (`app/render/sandbox.py`)

The one primitive every renderer goes through:

```python
@dataclass(frozen=True)
class SandboxLimits:
    memory: str            # e.g. "2g"
    cpus: str              # e.g. "1.0"
    pids_limit: int        # e.g. 256
    timeout_seconds: int   # wall-clock kill
    user: str              # e.g. "10001:10001" (non-root)

@dataclass(frozen=True)
class RunResult:
    exit_code: int         # 0 = ok; 124 reserved for timeout
    stdout: str
    stderr: str
    timed_out: bool

async def run_sandboxed(
    *, image: str, command: list[str], input_dir: Path, output_dir: Path, limits: SandboxLimits
) -> RunResult: ...
```

Implementation: `asyncio.create_subprocess_exec("docker", "run", ...)` with a generated `--name` so a timeout can `docker kill` it. The flag set, fixed for every invocation:

```
--rm --name <cid> --network=none --read-only
--cap-drop=ALL --security-opt=no-new-privileges
--user <limits.user> --memory <limits.memory> --cpus <limits.cpus>
--pids-limit <limits.pids_limit> --tmpfs /tmp:rw,size=64m
-v <input_dir>:/in:ro -v <output_dir>:/out
<image> <command...>
```

- **Timeout:** `asyncio.wait_for(proc.communicate(), limits.timeout_seconds)`; on `TimeoutError`, `docker kill <cid>` and return `RunResult(exit_code=124, timed_out=True, ...)`. Never leaks a running container.
- **Output contract:** the container writes `/out/scene.mp4` (or `/out/final.mp4`); the host reads it back from `output_dir` after a 0 exit. A 0 exit with a missing/zero-byte output is treated as a failure by the caller.
- **`get_sandbox_runner()`** returns the real `run_sandboxed` callable; it is the single monkeypatch seam (same pattern as `get_tts_client` / `get_storage`). Every unit test injects a fake that writes a canned MP4 to `output_dir` and returns a chosen `RunResult` — so no test touches Docker.

**`docker/render/Dockerfile`** — `algoreel-render`: a slim base with `ffmpeg` + one bundled TTF font (for `drawtext`) + a non-root user (uid/gid `10001`). No entrypoint logic needed in M4 (the host passes the full command); M5 adds `manim` (+ its TeX/cairo deps) to this same image and a small runner for the generated-code path.

---

## 5. `SceneRenderer` Protocol + `TrivialRenderer` (`app/render/base.py`, `trivial.py`)

The TRD §5.4 seam, adapted to the staging model so a renderer owns *what goes into `/in`* and *what command runs*:

```python
@dataclass(frozen=True)
class RenderInput:
    scene_index: int
    text: str               # narration to display
    audio_path: Path        # host path to the scene's wav (already staged)
    duration: Decimal       # measured audio length (scenes.duration_seconds)

class SceneRenderer(Protocol):
    async def render(self, *, job_id: int, render_in: RenderInput,
                     input_dir: Path, output_dir: Path) -> RunResult: ...

class RenderError(Exception):
    def __init__(self, scene_index: int, stderr: str) -> None: ...
```

`render(...)` stages its inputs into `input_dir`, builds the command, calls `run_sandboxed`, and returns the `RunResult` (the job layer turns a non-zero/timeout/empty-output result into a `RenderError` so it can be persisted to `renders.stderr`). `get_renderer()` returns the configured renderer; M4 returns `TrivialRenderer` unconditionally (M5 dispatches on `scene.renderer`).

**`TrivialRenderer`:**
- Writes `text.txt` (the scene narration) into `input_dir` — read by ffmpeg via `drawtext=textfile=/in/text.txt`, which sidesteps all shell-escaping of arbitrary narration (apostrophes, colons, newlines).
- Copies/links the scene audio to `input_dir/audio.wav`.
- Builds the command: a solid-background source (`-f lavfi -i color=c=<bg>:s=<size>:r=<fps>`), `-i /in/audio.wav`, a `drawtext` filter (centered, wrapped), `-t <duration>` to pin length to the audio, `-c:v libx264 -pix_fmt yuv420p -c:a aac -movflags +faststart /out/scene.mp4`.
- Output: a real, playable MP4 whose audio is the synthesized narration and whose length equals the scene's measured duration. Compute cost: $0 → `renders.cost_usd = 0`.

The compose path does not implement `SceneRenderer`; `compose_video` builds an `ffmpeg -f concat -safe 0 -i /in/list.txt -c copy /out/final.mp4` command and calls `run_sandboxed` directly with a read mount over the staged scene MP4s.

---

## 6. Render-pool jobs (`app/workers/render.py`)

**`render_scene(ctx, scene_id)`** — render pool, `max_jobs=1`:

1. Fresh `session_scope()`, storage, `get_renderer()`.
2. Load scene. **Idempotency:** `if scene.status == done: return` (resume / double-enqueue guard).
3. Resolve the scene's `AssetKind.AUDIO` asset and `storage.get(key)` its bytes into a per-job temp `input_dir` as `audio.wav`. (`output_dir` is a sibling temp dir.)
4. `scene_repo.update_status(scene_id, RENDERING)`; `RenderRepo.start_attempt(scene_id, attempt=1)`; commit.
5. `result = await renderer.render(...)`. If `result.exit_code != 0` or `result.timed_out` or `/out/scene.mp4` missing/empty → raise `RenderError(scene.index, result.stderr)`.
6. Read `/out/scene.mp4`; `storage.put("video/{job}/{scene}.mp4", bytes, "video/mp4")` → `AssetRepo.record(..., SCENE_MP4)`; `scene_repo.set_output_url(scene_id, storage.url(key))`; `update_status(scene_id, DONE)`; `RenderRepo.mark_succeeded(render_id, duration_ms)`; commit.
7. On `RenderError`: `RenderRepo.mark_failed(render_id, stderr)`; `update_status(scene_id, FAILED)`; commit; **re-raise** so Arq infra-retry (`max_tries`) applies and, on final failure, the exception is delivered to the orchestrator via `job.result()`.

**`compose_video(ctx, job_id)`** — render pool, trusted:

1. Fresh session, storage. **Idempotency:** `if job.output_url is not None: return`.
2. Load scenes ordered by `index`; `storage.get` each scene MP4 into `input_dir`; write `list.txt` (concat demuxer manifest, in index order).
3. `run_sandboxed(ffmpeg concat)` → `/out/final.mp4`; non-zero/empty → raise a `RenderError`-style failure surfaced to the orchestrator as `compose_error`.
4. `storage.put("video/{job}/final.mp4", bytes, "video/mp4")` → `AssetRepo.record(..., FINAL_MP4)`; `JobRepo.set_output_url(job_id, storage.url(key))`; commit.

**Temp-dir hygiene:** both jobs use `tempfile.TemporaryDirectory` for `/in` and `/out` staging (cleaned on exit); only storage holds durable artifacts. Container mounts are the host temp dirs.

---

## 7. Orchestrator rewiring + coordination (Approach A)

The orchestrator opens a render-queue pool once per run via `create_pool(redis_settings())` (Arq's `ArqRedis`), used to enqueue onto `render_pool` and read results.

**`RENDERING` block** (replaces [orchestrator.py:144-169](../../../app/workers/orchestrator.py)):
- Re-read scenes; for each scene whose status is not `done`, `await pool.enqueue_job("render_scene", scene.id, _queue_name=RENDER_QUEUE)` → collect `Job` handles.
- `await asyncio.gather(*[j.result(timeout=render_result_timeout_seconds) for j in handles])`.
- After each scene completes (re-read its row), emit a `progress` event with `stage="render"`, `current_scene`, `total`, and `set_progress` on the job; commit per scene (cancel-safe, mirrors the existing per-scene commit).
- If any `j.result()` raises (final infra failure or a `render_error`), `_fail(... {"type": "render_error", "scene_index": <if known>, "message": ...})` and return.
- Then `_transition(RENDERING → COMPOSING)`.

**`COMPOSING` block** (replaces [orchestrator.py:173-175](../../../app/workers/orchestrator.py)):
- `handle = await pool.enqueue_job("compose_video", job_id, _queue_name=RENDER_QUEUE)`; `await handle.result(timeout=compose_result_timeout_seconds)`.
- Emit a `progress` event with `stage="compose"`.
- On failure → `_fail(... {"type": "compose_error", "message": ...})`. Else `_transition(COMPOSING → DONE)`. The existing `_transition` already publishes the terminal `done` event; the frontend re-fetches the snapshot to pick up `output_url` (TRD §7 SSE contract — unchanged).

**Coordination = Approach A** (chosen over DB-poll and last-scene-triggers-compose): the orchestrator is the single place that holds the join. It is I/O-bound, so blocking a coroutine on `gather` for the render duration is free; Arq `keep_result` on the render worker makes `job.result()` work. Resume is the existing DB-state pattern — restart re-reads scenes, skips `done`, re-enqueues + awaits only the rest; the `render_scene` idempotency guard absorbs the rare double-run where a pre-crash job is still in flight.

`_assert_not_terminal` checkpoints (cancellation) are kept before fan-out and before compose. Killing in-flight containers on cancel is deferred (§2) — sub-second trivial renders make it moot until Manim.

---

## 8. Failure & resume semantics (M4)

- **Transient render failure** (worker crash, Redis blip, container OOM-kill): Arq `max_tries=2` re-runs the whole `render_scene`/`compose_video` job; idempotency guards prevent duplicate artifacts.
- **Hard render failure** (non-zero exit, timeout, empty output): the scene goes `failed`, a `renders` row records `failed` + stderr, and the orchestrator fails the **whole job** with a typed `render_error` (no `partially_failed` in M4 — see §2). A trivial-renderer hard failure indicates an infra/bug condition, not a content problem worth partial-resuming.
- **Compose failure:** job → `failed` with `compose_error`.
- **Idempotent resume:** `render_scene` skips `done` scenes; `compose_video` skips a job that already has `output_url`. An orchestrator re-delivery re-enqueues and awaits only incomplete scenes, then compose. This reuses the database-as-source-of-truth resume model already in the orchestrator (TRD §4.6) — no new checkpointing.

---

## 9. Configuration (`app/config.py`)

New fields (all defaulted; none newly required):

```python
render_image: str = "algoreel-render:m4"
render_video_size: str = "1280x720"
render_video_fps: int = Field(default=30, gt=0)
render_bg_color: str = "0x0B132B"
render_memory: str = "2g"
render_cpus: str = "1.0"
render_pids_limit: int = Field(default=256, gt=0)
render_user: str = "10001:10001"
render_timeout_seconds: int = Field(default=120, gt=0)     # container wall-clock
render_result_timeout_seconds: int = Field(default=900, gt=0)   # orchestrator await per scene
compose_result_timeout_seconds: int = Field(default=300, gt=0)  # orchestrator await for compose
```

`render_concurrency` is expressed as the render worker's `max_jobs=1` (TRD §4.2: concurrency per render worker is intentionally 1; scale by process count, `N = cores - 1`, at the deploy layer).

---

## 10. Worker wiring (`app/workers/arq_settings.py`)

- `RENDER_QUEUE = "render_pool"` as a module constant (mirrors the existing `ORCHESTRATOR_QUEUE` — queue names live in code, not config, matching the current pattern).
- Keep `WorkerSettings` (orchestrator) as-is, plus a render-queue pool helper the orchestrator imports.
- Add `RenderWorkerSettings`:
  - `functions = [render_scene, compose_video]`
  - `queue_name = "render_pool"`
  - `max_jobs = 1` (concurrency-1 per process)
  - `max_tries = 2`
  - `job_timeout` ≥ `render_timeout_seconds` + slack
  - `keep_result` > 0 (so the orchestrator can read job results)
  - `on_startup = configure_logging`
  - `redis_settings = redis_settings()`

`make worker` runs the orchestrator pool; `make render-worker` runs `arq app.workers.arq_settings.RenderWorkerSettings`. Both must run for a job to complete (documented in README quick-start).

---

## 11. Testing strategy

**Unit (fast, no Docker — the sandbox runner is faked):**
- `run_sandboxed` constructs the exact `docker run` argv (assert flags, mounts, image, command) with a faked `create_subprocess_exec`; timeout path issues `docker kill` and returns `exit_code=124, timed_out=True`.
- `TrivialRenderer.render` stages `text.txt` + `audio.wav` and builds the expected ffmpeg command; verifies `-t` equals the scene duration and the output target is `/out/scene.mp4`.
- `render_scene` job (faked `get_sandbox_runner` writes a canned MP4): asserts `SCENE_MP4` asset row, `scenes.output_url`, scene `done`, and a `renders` row `succeeded` with `duration_ms`. Failure variant (faked non-zero result): scene `failed`, `renders` row `failed` + stderr, exception raised.
- `compose_video` job (faked runner): asserts `FINAL_MP4` asset, `jobs.output_url`, idempotent skip when `output_url` already set.
- Orchestrator E2E: monkeypatch the render-queue `enqueue_job`/`result` to run `render_scene`/`compose_video` in-process against the faked runner (or stub the results) → a job walks `queued → … → done` with `stage="render"`/`stage="compose"` progress events and a non-null `output_url`. Scene-failure variant → job `failed` with `render_error`. Resume variant → pre-mark a scene `done`, assert it is not re-rendered.
- SSE contract regression ([tests/api/test_sse.py](../../../tests/api/test_sse.py)): assert `stage="render"` and `stage="compose"` events appear on the stream (mirrors the M3 `stage="tts"` assertion).

**Live integration — gated, manual, not CI:** `scripts/smoke_render.py` + `make smoke-render` behind `ALGOREEL_ALLOW_LIVE_RENDER=1` (mirrors `smoke-llm`/`smoke-tts`). Builds the image, renders one scene from a tiny canned wav, composes, and writes a real MP4 under `MEDIA_ROOT`. Excluded from CI because nested `docker run` inside the test container is heavier than the testcontainers Postgres/Redis the suite already provisions.

**Coverage note:** the live `run_sandboxed` Docker path is exercised only by the gated smoke (its argv construction and timeout branch are unit-tested via the faked subprocess); call this out as an intentional coverage gap, like the `OpenAITTSClient` live path in M3.

---

## 12. Observability & docs

- `docs/apis/videos.md`: document `progress.stage` values `render` (per-scene MP4) and `compose` (final concat), and that `output_url` is non-null on terminal `done`. Update the example SSE block to show a `render` and a `compose` progress event.
- `.env.example`: add the `render_*` block.
- `Makefile`: add `render-image` (`docker build -t algoreel-render:m4 docker/render`) and `render-worker`; extend `.PHONY` and `smoke-render`.
- README: note the two worker processes (`make worker` + `make render-worker`) and the `make render-image` prerequisite.

OTel spans / Prometheus metrics for the render+compose stages remain a TRD §8 day-one *target* deferred to M5 with the rest of the observability stack (consistent with M1–M3).

---

## 13. Migration triggers / what M5 unlocks

M4 lands the architecture; M5 makes the renders *good*:

- **`ManimRenderer`** behind `SceneRenderer` + **Pass-2 LLM** writing `scenes.manim_code` from `visual_prompt` + the measured `duration` → run the generated code via the *same* `run_sandboxed` harness (now genuinely sandboxing untrusted code).
- **Pass-2 critic + heterogeneous Sonnet→Opus retry + content-retry loop** (TRD §4.4, §5.2) inside `render_scene`.
- **`partially_failed` + `POST /resume`** once per-scene content failure is expected.
- **Container-kill-on-cancel** for long renders; **render-cost circuit breaker** before fan-out.
- **Object storage (R2)** when the single-box shared-filesystem assumption (§3) breaks, or burst render capacity (Modal/RunPod, TRD §4.9) is needed.
