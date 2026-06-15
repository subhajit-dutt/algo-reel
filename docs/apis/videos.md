# Videos

All routes require `Authorization: Bearer $APP_SHARED_SECRET`. Missing/wrong token → `401`.

Set once for the examples below:

```bash
export TOKEN=change-me-in-real-env
```

---

## `POST /api/videos` — Create a video job

Inserts a `jobs` row in `queued`, enqueues the orchestrator, returns the job snapshot. Worker walks the job through `queued → scripting → script_ready → rendering → composing → done` asynchronously.

Creation is rejected with `503` when no orchestrator worker is alive (arq health key `orchestrator_pool:health-check` absent — the worker refreshes it every 60 s while running). Without this guard the job would sit in `queued` forever. Start a worker with `make worker` and retry after the `Retry-After: 60` hint.

```bash
curl -sS -X POST http://localhost:8000/api/videos \
  -H "Authorization: Bearer $TOKEN" \
  -H "content-type: application/json" \
  -d '{
    "prompt": "Explain merge sort in 60 seconds",
    "renderer": "manim",
    "duration_target": 60,
    "voice": "alloy"
  }'
```

**Body fields**

| Field | Type | Constraints |
|---|---|---|
| `prompt` | string | 1–2000 chars |
| `renderer` | enum | `manim` \| `ai_image` |
| `duration_target` | int | `30` \| `60` \| `180` |
| `voice` | string | 1–64 chars; default `alloy` |

**Response 202**

```json
{
  "id": 42,
  "user_prompt": "Explain merge sort in 60 seconds",
  "renderer": "manim",
  "voice": "alloy",
  "duration_target_seconds": 60,
  "status": "queued",
  "progress": {},
  "output_url": null,
  "cost_usd": "0.0000",
  "error": null,
  "scenes": [],
  "created_at": "2026-05-19T18:00:00Z",
  "updated_at": "2026-05-19T18:00:00Z"
}
```

**Errors**

| Status | When |
|---|---|
| 401 | Missing/invalid bearer token |
| 422 | Validation failure (empty prompt, bad enum, wrong duration) |
| 503 | No live orchestrator worker consuming the queue (`Retry-After: 60`); no job row is created |

---

## `GET /api/videos/{id}` — Job snapshot

Returns the full current state of the job, including ordered `scenes`.

```bash
curl -sS http://localhost:8000/api/videos/42 \
  -H "Authorization: Bearer $TOKEN"
```

**Response 200**

```json
{
  "id": 42,
  "user_prompt": "Explain merge sort in 60 seconds",
  "renderer": "manim",
  "voice": "alloy",
  "duration_target_seconds": 60,
  "status": "rendering",
  "progress": {"current_scene": 2, "total": 4, "stage": "render"},
  "output_url": null,
  "cost_usd": "0.0067",
  "error": null,
  "scenes": [
    {
      "id": 101,
      "index": 0,
      "narration": "We begin with a single unsorted array...",
      "visual_prompt": "diagram of an unsorted array of 8 boxes",
      "duration_seconds": "15.00",
      "status": "done",
      "output_url": null,
      "created_at": "2026-05-19T18:00:05Z",
      "updated_at": "2026-05-19T18:00:09Z"
    }
  ],
  "created_at": "2026-05-19T18:00:00Z",
  "updated_at": "2026-05-19T18:00:09Z"
}
```

`status` is one of `queued, scripting, script_ready, rendering, composing, done, failed, cancelled, partially_failed`.

`error` is populated on `failed` jobs, e.g. `{"type": "budget_exceeded", "reason": "scene_count", "value": "20"}`.

**Errors**

| Status | When |
|---|---|
| 401 | Missing/invalid bearer token |
| 404 | Job id not found |

---

## `DELETE /api/videos/{id}` — Cancel a job

Sets `status='cancelled'` using a conditional UPDATE that only succeeds when the job is in a non-terminal state. The worker observes the cancel at its next checkpoint and stops.

```bash
curl -sS -X DELETE http://localhost:8000/api/videos/42 \
  -H "Authorization: Bearer $TOKEN"
```

**Response 200** — same shape as `GET /api/videos/{id}` with `status: "cancelled"`.

Also publishes a `cancelled` SSE event on the job's progress channel so any active stream subscriber closes immediately rather than waiting for the worker to observe the cancel at its next checkpoint.

**Errors**

| Status | When |
|---|---|
| 401 | Missing/invalid bearer token |
| 404 | Job id not found |
| 409 | Job is already in a terminal state (`done`, `failed`, `cancelled`, `partially_failed`) |

---

## `GET /api/videos/{id}/events` — SSE progress stream

Server-Sent Events stream. Emits a `snapshot` event first (the current job state) then forwards every `transition` / `progress` / `failed` / `done` / `cancelled` event published by the worker or the cancel endpoint. Closes on the first terminal status received, or if the job was already terminal at request time.

```bash
curl -N -sS http://localhost:8000/api/videos/42/events \
  -H "Authorization: Bearer $TOKEN"
```

(`-N` disables curl's output buffering so events render as they arrive.)

**Response 200** — `text/event-stream`, e.g.:

```
event: snapshot
data: {"event":"snapshot","job_id":42,"status":"queued","progress":{},"scene_id":null,"error":null,"ts":"2026-05-19T18:00:00Z"}

event: transition
data: {"event":"transition","job_id":42,"status":"scripting","progress":{},"scene_id":null,"error":null,"ts":"2026-05-19T18:00:01Z"}

event: progress
data: {"event":"progress","job_id":42,"status":"script_ready","progress":{"current_scene":1,"total":3,"stage":"tts"},"scene_id":101,"error":null,"ts":"2026-05-19T18:00:04Z"}

event: progress
data: {"event":"progress","job_id":42,"status":"rendering","progress":{"current_scene":1,"total":3,"stage":"render"},"scene_id":101,"error":null,"ts":"2026-05-19T18:00:06Z"}

event: progress
data: {"event":"progress","job_id":42,"status":"composing","progress":{"stage":"compose"},"scene_id":null,"error":null,"ts":"2026-05-19T18:00:20Z"}

event: done
data: {"event":"done","job_id":42,"status":"done","progress":{},"scene_id":null,"error":null,"ts":"2026-05-19T18:00:14Z"}
```

The SSE `event:` line mirrors the JSON payload's `event` field; clients can dispatch via `EventSource.addEventListener("done", …)`. Heartbeat ping every 15 s.

The `progress.stage` field is one of `"tts"` (per-scene narration synthesis, `status` = `script_ready`), `"render"` (per-scene MP4, `status` = `rendering`), or `"compose"` (final concat, `status` = `composing`). On terminal `done`, `output_url` is non-null and points at the final MP4.

**Errors**

| Status | When |
|---|---|
| 401 | Missing/invalid bearer token |
| 404 | Job id not found |

---

## `POST /api/videos/{id}/resume` — Resume a partially-failed job

Re-queues the failed scenes of a `partially_failed` job and transitions it back to `rendering`. Only jobs in `partially_failed` status can be resumed; any other status returns 409.

```bash
curl -sS -X POST http://localhost:8000/api/videos/42/resume \
  -H "Authorization: Bearer $TOKEN"
```

**Response 200** — same shape as `GET /api/videos/{id}` with `status: "rendering"`.

Failed scenes are reset to `pending` and the orchestrator re-enqueues the render task.

**Errors**

| Status | When |
|---|---|
| 401 | Missing/invalid bearer token |
| 404 | Job id not found |
| 409 | Job is not in `partially_failed` status |
| 503 | No live orchestrator or render worker (`Retry-After: 60`) |
