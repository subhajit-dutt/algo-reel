// Empty string => same-origin requests (FastAPI serves the static bundle).
// In dev, set NEXT_PUBLIC_API_BASE=http://localhost:8000.
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

export const TOKEN_STORAGE_KEY = "algoreel.token";
export const RECENT_JOBS_STORAGE_KEY = "algoreel.recent_jobs";
export const RECENT_JOBS_LIMIT = 12;
