# Algo-Reel Milestone 3 — TTS + Local Audio Storage

**Status:** Approved (brainstorming)
**Owner:** Subhajit Dutta
**Date:** 2026-06-07
**Related:** [docs/trd.md](../../trd.md), [M1 design](2026-05-19-algo-reel-m1-design.md), [M2 design](2026-05-19-algo-reel-m2-design.md)

---

## 1. Purpose

Give every scene real spoken audio. Replace the M2 placeholder where `scenes.duration_seconds` carries the LLM's *proposed* duration with a true, measured duration derived from synthesized speech. This is the "audio first, then animation" rule from TRD §5.3: the renderer (M4) must be constrained to the exact length of the narration audio, so the audio — and its measured duration — has to exist before any render fan-out.

This milestone is "done" when:

- The orchestrator, after `SCRIPT_READY`, synthesizes one audio file per scene via a direct OpenAI TTS call, writes each file to local storage, records an `assets` row (`kind='audio'`), and overwrites `scenes.duration_seconds` with the measured audio length.
- `jobs.cost_usd` includes the accumulated TTS spend (on top of the M2 script-gen cost) via the existing additive `add_cost` channel.
- If any scene's TTS fails after transient retries, the whole job goes `failed` with a typed `tts_error` — no partial render of an audio-less video.
- Re-delivery of a partially-voiced job (Arq `max_tries`) does not re-bill TTS for scenes already voiced (idempotent on the `assets` unique key).
- Integration tests cover the orchestrator E2E with a **fake TTS client** writing to a **tmp media root** — no OpenAI call and no network in CI.

---

## 2. Scope

### In scope

- `app/tts/` package: a direct `AsyncOpenAI` audio client, a duration-derived pricing table, and a `synthesize_scene(...)` entry point.
- `app/storage/` package: a `Storage` Protocol + a `LocalStorage` implementation writing under a configured `MEDIA_ROOT`.
- `AssetRepo.record(...)` — first real writes to the `assets` table.
- `SceneRepo.set_duration(scene_id, seconds)` — overwrite the LLM placeholder with measured audio length.
- A new orchestrator sub-stage (between `SCRIPT_READY` and `RENDERING`) that fans out TTS across scenes with `asyncio.gather`, bounded by a semaphore.
- TTS cost accumulated into `jobs.cost_usd`.
- `progress` SSE events with `stage="tts"` during synthesis (reuses the M2 `ProgressPublisher`; no SSE contract change).
- Tests: unit (fake client synth, duration parsing, pricing, local storage round-trip, idempotency skip) + integration (orchestrator E2E with fake client + tmp media root). `make smoke-tts` hits real OpenAI behind an env flag.

### Out of scope (deferred)

- **Object storage (MinIO / Cloudflare R2) + signed URLs.** Deliberately deferred — local filesystem is sufficient for the documented single-box v1 deployment (TRD §4.9). The `Storage` interface makes the swap a one-class change. See §7 and §13 for the migration trigger.
- **ElevenLabs (per-job flag).** TRD §5.3 gates it behind a flag; no signal yet that the OpenAI default is insufficient. The `TTSClient` Protocol leaves room to add it without touching callers.
- **Pass 2 — Manim code generation + content-retry loop.** M4.
- **Scene MP4 / FFmpeg concat / `scenes.output_url`.** M4. The `RENDERING` loop stays an M1/M2 stub; M3 only feeds it real per-scene durations.
- **A dedicated `voicing` job status.** TTS is a sub-stage of the existing `SCRIPT_READY → RENDERING` flow; the `Job.status` enum (fixed in TRD §6) is unchanged. Progress is surfaced via `stage="tts"` events, not a new status.
- **`style_guide`-driven TTS instructions.** M3 uses a static `TTS_INSTRUCTIONS` setting; per-video voice steering from `VideoScript.style_guide` is a later refinement.
- **OTel / Prometheus instrumentation** of the TTS stage. M5.

---

## 3. Architecture additions

```
app/
├── tts/
│   ├── __init__.py
│   ├── client.py          # TTSClient Protocol + OpenAITTSClient (AsyncOpenAI audio.speech)
│   ├── pricing.py         # TTS_PRICING (per-minute) + compute_tts_cost(model, audio_seconds)
│   ├── duration.py        # wav_duration_seconds(data: bytes) -> Decimal  (stdlib `wave`)
│   └── synthesizer.py     # synthesize_scene(...) -> SynthesisResult
└── storage/
    ├── __init__.py
    ├── base.py            # Storage Protocol + StoredObject dataclass
    └── local.py           # LocalStorage(media_root)

app/repositories/asset_repo.py   # NEW — AssetRepo.record(...) + has_asset(...)
app/repositories/scene_repo.py   # + set_duration(scene_id, seconds)
app/workers/orchestrator.py      # + voicing sub-stage in the SCRIPT_READY block
app/config.py                    # + openai_api_key, tts_*, media_root
```

No new Alembic migration. M1 already provisions the `assets` table (`kind`, `storage_key`, `bytes`, `content_type`, unique `(job_id, scene_id, kind)`) and `scenes.duration_seconds` `Numeric(6,2)`. `AssetKind.AUDIO` already exists in `app/domain/enums.py`.

### Layering rules (additive — same as M1/M2)

- `app/tts/` is a leaf module: depends only on `openai`, `app.config`, stdlib `wave`, and `app/domain`. No dependency on `repositories/`, `services/`, or `db/`.
- `app/storage/` is a leaf module: depends only on stdlib + `app.config`. No DB, no network.
- `AssetRepo` is the only writer to the `assets` table. `SceneRepo.set_duration` is the only writer of post-TTS durations.
- `workers/orchestrator.py` is the only caller of `synthesize_scene`, `Storage.put`, and `AssetRepo.record`. It wires tts → storage → repos; the leaf modules never call each other.

---

## 4. TTS provider — OpenAI (direct)

Unlike the LLM path (M2, via OpenRouter), TTS calls go **directly to OpenAI**. OpenRouter is a chat-completions gateway and does not proxy the `audio/speech` endpoint, so a separate key and client are required. This is a deliberate, documented divergence from the one-gateway principle, scoped to the single TTS callsite.

### Model correction

TRD §5.3 names `gpt-4o-tts` (full). **No such model exists in OpenAI's catalog.** The steerable TTS model that supports the `instructions=` field — the capability TRD §5.3 actually wants — is **`gpt-4o-mini-tts`**. (`tts-1` / `tts-1-hd` exist but explicitly do *not* support `instructions=`.) M3 uses `gpt-4o-mini-tts`, config-driven so a future "full" model is a one-line env change.

### Configuration

| Env var | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | (required) | secret; direct OpenAI, distinct from `OPENROUTER_API_KEY` |
| `TTS_MODEL` | `gpt-4o-mini-tts` | steerable TTS model |
| `TTS_VOICE_DEFAULT` | `coral` | fallback when `Job.voice` is empty |
| `TTS_INSTRUCTIONS` | `Calm tutorial voice, clear pacing, slight pause between sentences.` | passed as `instructions=` |
| `TTS_RESPONSE_FORMAT` | `wav` | stdlib `wave` reads duration; no ffmpeg in M3 |
| `TTS_TIMEOUT_SECONDS` | `60` | per-call wall clock |
| `TTS_MAX_RETRIES` | `2` | transient-failure retries inside the client |
| `TTS_MAX_CONCURRENCY` | `4` | semaphore bound on the per-scene fan-out |
| `MEDIA_ROOT` | `./.media` | local storage root (gitignored) |

`Job.voice` (already on the model) selects the voice; `TTS_VOICE_DEFAULT` is the fallback. `instructions` is static in M3 (`TTS_INSTRUCTIONS`).

### `TTSClient` Protocol + OpenAI implementation

```python
class TTSClient(Protocol):
    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes: ...

class OpenAITTSClient:
    """Direct OpenAI audio.speech client. Retries transient failures TTS_MAX_RETRIES times."""
    def __init__(self, client: AsyncOpenAI, model: str, response_format: str, max_retries: int): ...
    async def synthesize(self, *, text: str, voice: str, instructions: str) -> bytes:
        # client.audio.speech.create(model=..., voice=..., input=text,
        #                            instructions=..., response_format=...)
        # returns raw audio bytes
```

A module-level `get_tts_client()` (mirrors `get_settings`'s cached-accessor shape) builds the `OpenAITTSClient` from settings. Tests override this seam with a fake client (see §11).

### Cost — derived from duration, not usage

**The `audio/speech` endpoint returns raw audio bytes, not a `usage` object.** So TTS cost cannot be read back from the response the way LLM cost is in M2. `gpt-4o-mini-tts` is billed primarily on audio-output tokens, which track audio length; text input is a rounding error at narration sizes (≤300 chars/scene). We therefore compute cost from the **measured audio duration**, which we have exactly:

```python
@dataclass(frozen=True)
class TTSPricing:
    per_minute_usd: Decimal

TTS_PRICING: dict[str, TTSPricing] = {
    "gpt-4o-mini-tts": TTSPricing(per_minute_usd=Decimal("0.015")),  # verify vs current pricing at impl
}

def compute_tts_cost(model: str, *, audio_seconds: Decimal) -> Decimal:
    if model not in TTS_PRICING:
        raise UnknownModelError(...)            # no silent zero — same rule as llm/pricing.py
    rate = TTS_PRICING[model].per_minute_usd
    return ((audio_seconds / Decimal(60)) * rate).quantize(Decimal("0.0001"), ROUND_HALF_UP)
```

Rationale for a static per-minute table over reading usage: the endpoint gives no usage; duration is exact; the table is a one-line PR to re-sync when OpenAI changes pricing. The `0.015` default is a placeholder to be confirmed against OpenAI's current pricing page during implementation.

---

## 5. Synthesizer contract

```python
@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    content_type: str        # "audio/wav"
    duration_seconds: Decimal
    cost_usd: Decimal

async def synthesize_scene(
    *,
    narration: str,
    voice: str,
    client: TTSClient | None = None,   # defaults to get_tts_client(); tests inject a fake
) -> SynthesisResult:
    """Synthesize one scene's narration. Raises on TTS failure after the client's retries."""
```

Flow: call `client.synthesize(...)` → measure duration from the returned bytes (`tts.duration.wav_duration_seconds`) → `compute_tts_cost(model, audio_seconds=duration)` → return all four fields. No DB, no filesystem — pure synthesis. The orchestrator owns persistence.

### Duration measurement

`tts/duration.py` reads WAV bytes with the stdlib `wave` module — `frames / framerate` → seconds, quantized to `Decimal("0.01")` to fit `Numeric(6,2)`. No third-party dependency, no ffmpeg/ffprobe. (Choosing `TTS_RESPONSE_FORMAT=wav` is precisely what buys this; a future switch to mp3 would require `mutagen` or ffprobe and is out of scope.)

---

## 6. Storage layer (local)

```python
@dataclass(frozen=True)
class StoredObject:
    key: str           # storage key persisted to assets.storage_key
    bytes: int         # byte length, persisted to assets.bytes

class Storage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> StoredObject: ...
    def url(self, key: str) -> str: ...   # local: file:// path; R2 later: signed URL

class LocalStorage:
    def __init__(self, media_root: Path): ...
    async def put(self, key, data, content_type) -> StoredObject:
        # mkdir -p (media_root / key).parent; write bytes; return StoredObject(key, len(data))
```

- **Key scheme:** `audio/{job_id}/{scene_id}.wav`. Deterministic, collision-free, mirrors a future S3 key layout so the migration is purely a backend swap.
- `content_type` (`audio/wav`) and byte length are persisted to the `assets` row.
- `media_root` defaults to `./.media` and is added to `.gitignore`. The directory is created on first write.
- `Storage.put` is `async` even though local I/O is synchronous: it keeps the interface identical to the future async S3 client so the orchestrator's call sites and the `Storage` Protocol don't change on migration. The local implementation does the small write inline (sub-millisecond for a few-hundred-KB WAV); we do not thread-pool it.

---

## 7. Orchestrator changes — the voicing sub-stage

The voicing work lands **inside the existing `SCRIPT_READY` block, before the transition to `RENDERING`** — not in a new status. Placement matches TRD §5.3 (TTS fans out in the orchestrator pool) and keeps `Job.status` unchanged.

```python
if current == JobStatus.SCRIPT_READY:
    await _voice_all_scenes(session, job, scene_repo, asset_repo, storage, publisher)
    await _transition(job_repo, publisher, job_id, SCRIPT_READY, RENDERING)
    current = RENDERING
```

`_voice_all_scenes`:

1. `scenes = await scene_repo.list_by_job(job_id)`.
2. Bound a `asyncio.Semaphore(TTS_MAX_CONCURRENCY)`; `asyncio.gather` over scenes.
3. Per scene (under the semaphore):
   - **Idempotency skip:** if `await asset_repo.has_asset(job_id, scene.id, AssetKind.AUDIO)` → skip (already voiced on a prior attempt).
   - `result = await synthesize_scene(narration=scene.narration, voice=job.voice or TTS_VOICE_DEFAULT)`.
   - `stored = await storage.put(f"audio/{job_id}/{scene.id}.wav", result.audio_bytes, result.content_type)`.
   - `await asset_repo.record(job_id, scene.id, AssetKind.AUDIO, stored.key, stored.bytes, result.content_type)`.
   - `await scene_repo.set_duration(scene.id, result.duration_seconds)`.
   - accumulate `result.cost_usd`.
4. After gather: `await job_repo.add_cost(job_id, total_tts_cost)`; `await session.commit()`.
5. Publish a `progress` event per completed scene: `{"current_scene": i+1, "total": n, "stage": "tts"}`.

### Concurrency + the DB session

The existing orchestrator uses a single `AsyncSession` (`session_scope`). A SQLAlchemy `AsyncSession` is **not** safe for concurrent use across `asyncio.gather` tasks. Resolution: the **synthesis + storage write** (the slow, I/O-bound, network parts) run concurrently under the semaphore and return plain `SynthesisResult` + `StoredObject` values; the **DB writes** (`asset_repo.record`, `scene_repo.set_duration`, `add_cost`) are applied **sequentially on the single session** after each task resolves (or in a post-gather loop). Concurrency is on the OpenAI calls — the win TRD §5.3 cares about — not on the session. This keeps one transaction and avoids session races.

### Cancellation

The `_assert_not_terminal()` checkpoint pattern from M1/M2 is reused: check job status before launching the fan-out and before the `RENDERING` transition. A `DELETE` mid-synthesis lets in-flight OpenAI calls complete (no request cancellation in v1, same as the M2 LLM call), but the post-gather DB writes and the transition become no-ops once the row is `cancelled`. Audio already written to disk for completed scenes is retained (cheap; cleaned by retention later).

---

## 8. Failure, idempotency, resume

- **Transient retries** live inside `OpenAITTSClient` (`TTS_MAX_RETRIES`, on network / 5xx). This is infra-class retry, analogous to Arq's `max_tries` but at call granularity.
- **Hard failure → fail the whole job.** If a scene's TTS still fails after retries, `_voice_all_scenes` raises; the orchestrator catches it and calls `_fail(... error={"type":"tts_error","scene_index":i,"message":str(e)})`, publishes a `failed` SSE event, and exits. No partial — a video with a missing scene's audio is not renderable, and TTS failures are infra-class, not content-class (so the M4 `partially_failed` + resume path does not apply). (Confirmed design decision.)
- **Idempotency anchor:** the `assets` unique constraint `(job_id, scene_id, kind='audio')`. On Arq `max_tries` re-delivery, the `has_asset` check skips already-voiced scenes, so TTS is never re-billed — the same guard pattern as M2's `if job.script is None` resume guard for script-gen.
- **`gather` semantics:** use `asyncio.gather(..., return_exceptions=False)` so the first scene failure cancels the rest and propagates promptly to `_fail`. We are failing the whole job anyway; there is no value in finishing the other scenes.

---

## 9. Error handling (per CLAUDE.md — no fallbacks)

| Failure | Behavior |
|---|---|
| OpenAI network / 5xx | Retried `TTS_MAX_RETRIES` inside the client. On exhaustion → raise → `status='failed'`, `error={type:"tts_error", scene_index, message}`, publish `failed`. Arq retries the whole job up to `max_tries=2`. |
| Non-WAV / unreadable audio bytes | `wave` raises → `tts_error`. (Should not happen with `response_format=wav`; surfaced loudly, not swallowed.) |
| Unknown model in `TTS_PRICING` | `UnknownModelError` — raised at synth time, caught as `tts_error`. Catches a misconfigured `TTS_MODEL`. |
| Job cancelled mid-fan-out | Post-gather writes + transition become no-ops via the conditional `UPDATE`; checkpoint raises `_AbortedError`. |
| Re-delivery of a partially-voiced job | `has_asset` skips voiced scenes; only unvoiced scenes are synthesized. No double-billing. |

No `try/except` that swallows. No bespoke backoff beyond the client's bounded retry. Arq owns job-level infra retry.

---

## 10. Config additions & updated `.env.example`

`app/config.py` gains (Pydantic settings, same style as M2):

```python
openai_api_key: str = Field(min_length=1)
tts_model: str = "gpt-4o-mini-tts"
tts_voice_default: str = "coral"
tts_instructions: str = "Calm tutorial voice, clear pacing, slight pause between sentences."
tts_response_format: str = "wav"
tts_timeout_seconds: int = Field(default=60, gt=0)
tts_max_retries: int = Field(default=2, ge=0)
tts_max_concurrency: int = Field(default=4, gt=0)
media_root: str = "./.media"
```

`.env.example` — the reserved `S3_*` block (currently "Unused until M3") is **repurposed**: it is the future R2 surface, *not* used in M3. M3 uses local disk via `MEDIA_ROOT`:

```
# TTS (OpenAI direct — OpenRouter does not proxy the audio endpoint)
OPENAI_API_KEY=
TTS_MODEL=gpt-4o-mini-tts
TTS_VOICE_DEFAULT=coral
TTS_INSTRUCTIONS=Calm tutorial voice, clear pacing, slight pause between sentences.
TTS_RESPONSE_FORMAT=wav
TTS_TIMEOUT_SECONDS=60
TTS_MAX_RETRIES=2
TTS_MAX_CONCURRENCY=4

# Local audio storage (M3). Object storage (R2) is a later milestone.
MEDIA_ROOT=./.media

# Reserved for the object-storage migration (R2) — unused while MEDIA_ROOT is local
S3_ENDPOINT_URL=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_BUCKET=
```

`.gitignore` gains `.media/`.

---

## 11. Testing strategy

- **No live OpenAI in CI, no network.** All synthesis goes through a **`FakeTTSClient`** that returns a fixed, valid WAV blob of a known duration (a tiny generated WAV header + N frames). Injected by overriding the `get_tts_client()` seam (monkeypatch), mirroring M2's `Agent.override(TestModel(...))`.
- **Unit:**
  - `tts.duration.wav_duration_seconds` — table-driven against WAV blobs of known length.
  - `tts.pricing.compute_tts_cost` — per-minute math + unknown-model raise.
  - `synthesize_scene` — fake client → asserts `SynthesisResult` fields (duration, cost, content_type).
  - `LocalStorage.put` — round-trip on `tmp_path`: file exists, bytes match, `StoredObject` correct; nested-dir creation.
  - `AssetRepo.record` / `has_asset` — insert + idempotent re-check; unique-constraint conflict surfaces.
  - `SceneRepo.set_duration` — overwrites the placeholder value.
- **Integration (orchestrator E2E):**
  - Fake TTS client + `tmp_path` media root. Asserts: every scene gets a measured `duration_seconds` (≠ the LLM placeholder), one `assets` row per scene (`kind='audio'`, correct `storage_key`/`bytes`/`content_type`), audio files on disk, and `jobs.cost_usd` == script cost + Σ TTS cost.
  - **Failure path:** fake client raises on scene index k → assert `status='failed'`, `error.type == "tts_error"`, `error.scene_index == k`, and no `RENDERING` transition.
  - **Idempotency:** pre-seed audio assets for scenes 0..k, run the voicing stage, assert the fake client is called only for the remaining scenes and cost reflects only those.
  - **SSE:** assert the event stream now includes `progress` events with `stage="tts"` before the `RENDERING` transition.
- **Manual smoke:** `make smoke-tts` synthesizes a real scene against OpenAI, writes to `./.media`, prints the measured duration and cost. Behind `ALGOREEL_ALLOW_LIVE_TTS=1` (mirrors `smoke-llm`). New `scripts/smoke_tts.py`.
- **Coverage target:** keep ≥ 80% on `app/`; new packages held to the same bar.

---

## 12. Dependencies, runtime, Makefile

- **No new third-party dependency.** `openai` is already pinned (M2, used by PydanticAI's provider) and exposes `audio.speech`. WAV duration uses the stdlib `wave`. Local storage uses stdlib `pathlib`.
- **No new infra.** Still Postgres + Redis; no MinIO container, no new Docker service.
- **Process topology unchanged:** `uvicorn` + one `arq` orchestrator worker. Render pool is still M4. TTS runs in the orchestrator pool (I/O-bound, correct per TRD §4.2 / §5.3).
- **Makefile:** add `smoke-tts` (parallel to `smoke-llm`) and add `smoke-tts` to `.PHONY`.

```make
smoke-tts:
	ALGOREEL_ALLOW_LIVE_TTS=1 uv run python -m scripts.smoke_tts $(args)
```

---

## 13. Risks & trade-offs (M3-specific)

- **Local-disk storage couples the orchestrator and the M4 render pool to a shared filesystem.** Fine under the documented single-box v1 deployment (TRD §4.9: one orchestrator + render workers on one box), where both processes see the same `MEDIA_ROOT`. **Migration trigger:** the moment renders burst to a second box / Modal / RunPod, audio must move to object storage (R2) — at which point `LocalStorage` is replaced by an `S3Storage` implementing the same `Storage` Protocol, and `Storage.url()` returns a signed URL instead of a `file://` path. No call-site changes. This is the one load-bearing simplification in M3 and is called out so it isn't forgotten.
- **TTS cost is estimated, not metered.** The speech endpoint returns no usage; cost is `duration × per-minute rate`. Accurate enough for budget tracking at ≤20 users, but it will drift from the real invoice if OpenAI's pricing or token model changes. Mitigation: the `TTS_PRICING` table is a one-line re-sync, and `job_cost_usd` is for alerting, not billing.
- **`gpt-4o-mini-tts` is the steerable model, not the TRD's "full" model.** Quality is a step below an eventual full model but well inside budget and supports `instructions=`. If prosody proves insufficient, the model is a config swap (and ElevenLabs remains the deferred premium path).
- **WAV is uncompressed.** A few hundred KB/scene; a 12-scene video is a few MB on local disk. Negligible at this scale; if storage volume ever matters, switch `TTS_RESPONSE_FORMAT` to mp3 and add a duration reader (`mutagen`). Out of scope now.
- **First write of the `assets` table.** The unique key `(job_id, scene_id, kind)` is now load-bearing for idempotency. A wrong key scheme would silently re-bill on retry; covered by the idempotency integration test.

---

## 14. Future scope (deferred from M3)

- **Object storage (MinIO local / R2 prod) + signed URLs** → next storage milestone or M4 (the renderer's scene MP4 also needs it). `S3Storage` implements the existing `Storage` Protocol.
- **ElevenLabs per-job flag** → behind the `TTSClient` Protocol when premium voice is needed.
- **`style_guide`-driven TTS `instructions`** → derive per-video voice steering from `VideoScript.style_guide`.
- **OTel span around `tts_per_scene`** → M5 (TRD §8).
- **Audio retention / lifecycle cleanup** → with the storage migration.

---

## 15. Open questions

None blocking M3 implementation.

---

## 16. Self-review notes

- Every M3 item from the M1 future-scope (§11 "M3 — TTS + object storage") and the code-walkthrough §9 map to in-scope (TTS per scene, audio-first durations, `assets` rows, cost accumulation) or explicitly-deferred-with-reason (object storage → local disk per decision; ElevenLabs; signed URLs). The object-storage deviation from the original M3 plan is called out in §2, §7, §13, §14.
- No `TBD` / `TODO` placeholders. The two values flagged "verify at impl" (the `0.015` per-minute rate and the exact `gpt-4o-mini-tts` model id) are external facts to confirm against OpenAI's live docs, not unresolved design.
- Naming consistent across sections: `synthesize_scene`, `SynthesisResult`, `TTSClient`, `OpenAITTSClient`, `get_tts_client`, `Storage`, `LocalStorage`, `StoredObject`, `AssetRepo`, `compute_tts_cost`, `TTS_PRICING`, `MEDIA_ROOT`, `tts_error`, `stage="tts"`, key scheme `audio/{job_id}/{scene_id}.wav`.
- Concurrency-vs-session hazard explicitly resolved in §7 (parallel I/O, sequential DB writes on the single session).
- Single implementation plan can cover the milestone; no decomposition required.
