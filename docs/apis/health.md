# Health

## `GET /healthz` — Liveness

Process is up. No dependency checks.

```bash
curl -sS http://localhost:8000/healthz
```

**Response 200**

```json
{"status": "ok"}
```

**Errors** — none (unauthenticated, no dependencies).

---

## `GET /readyz` — Readiness

Pings Postgres and Redis. Used by orchestrators / load balancers to gate traffic.

```bash
curl -sS http://localhost:8000/readyz
```

**Response 200**

```json
{"postgres": true, "redis": true}
```

**Errors**

| Status | Body | When |
|---|---|---|
| 503 | `{"detail": {"postgres": false, "redis": true}}` | Postgres ping failed |
| 503 | `{"detail": {"postgres": true, "redis": false}}` | Redis ping failed |
