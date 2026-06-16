import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { JobError, Renderer } from "@/types/api";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatRenderer(renderer: Renderer): string {
  return renderer.replace("_", " · ");
}

/** Human-readable failure reason, in precedence order. */
export function jobErrorReason(error: JobError | null | undefined): string | undefined {
  return error?.reason ?? error?.message ?? error?.type;
}

export function formatCost(usd: string | number): string {
  const n = typeof usd === "string" ? Number(usd) : usd;
  if (!Number.isFinite(n)) return "$0.0000";
  return `$${n.toFixed(4)}`;
}

export function formatDuration(seconds: string | number): string {
  const n = typeof seconds === "string" ? Number(seconds) : seconds;
  if (!Number.isFinite(n)) return "0s";
  if (n < 60) return `${n.toFixed(1).replace(/\.0$/, "")}s`;
  const m = Math.floor(n / 60);
  const s = Math.round(n - m * 60);
  return `${m}m ${s}s`;
}

export function truncate(s: string, max = 80): string {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}
