# algo-reel API

Base URL (local): `http://localhost:8000`

Auth: all `/api/*` routes require `Authorization: Bearer $APP_SHARED_SECRET`. `/healthz` and `/readyz` are unauthenticated.

| Method | Path | Doc |
|---|---|---|
| GET | `/healthz` | [health.md](health.md) |
| GET | `/readyz` | [health.md](health.md) |
| POST | `/api/videos` | [videos.md](videos.md) |
| GET | `/api/videos/{id}` | [videos.md](videos.md) |
| DELETE | `/api/videos/{id}` | [videos.md](videos.md) |
| GET | `/api/videos/{id}/events` | [videos.md](videos.md) |
