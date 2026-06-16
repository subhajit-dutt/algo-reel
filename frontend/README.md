# algo-reel frontend

Next.js 15 (App Router) static export. The build output lands in `frontend/out/` and is mounted by the FastAPI server via `app/static.py`.

## Dev

```bash
# from repo root
make frontend-install
make frontend-build      # writes frontend/out/

# or, dev against running backend on :8000
cd frontend
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

In dev mode the app talks to FastAPI on `:8000`. In production it runs same-origin (FastAPI serves the static bundle).

## Auth

On first load the app prompts for the bearer token (the server's `APP_SHARED_SECRET`). It's stored in `localStorage["algoreel.token"]`. A 401 clears it and re-prompts.

## Routing under static export

`output: 'export'` cannot generate per-job pages at build time. So there is one client-side root (`app/page.tsx`) that reads `usePathname()` and renders either `HomeView` or `VideoDetailView`. Deep links work because `_SpaStaticFiles` falls back to `index.html` for unknown paths.
