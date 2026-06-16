import { RECENT_JOBS_LIMIT, RECENT_JOBS_STORAGE_KEY } from "@/config";

function read(): number[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(RECENT_JOBS_STORAGE_KEY);
  if (!raw) return [];
  const parsed = JSON.parse(raw) as unknown;
  if (!Array.isArray(parsed)) return [];
  return parsed.filter((x): x is number => typeof x === "number");
}

function write(ids: number[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(RECENT_JOBS_STORAGE_KEY, JSON.stringify(ids));
  window.dispatchEvent(new Event("algoreel:recent-changed"));
}

export function getRecentIds(): number[] {
  return read();
}

export function pushRecentId(id: number): void {
  const existing = read().filter((x) => x !== id);
  const next = [id, ...existing].slice(0, RECENT_JOBS_LIMIT);
  write(next);
}

export function removeRecentId(id: number): void {
  const next = read().filter((x) => x !== id);
  write(next);
}
