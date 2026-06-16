"use client";

import { useEffect, useState } from "react";

import type { JobResponse } from "@/types/api";

interface RenderStageProps {
  job: JobResponse;
}

const STAGE_LABEL: Record<string, string> = {
  queued: "queued · waiting for a worker",
  scripting: "drafting the script",
  script_ready: "script ready · fanning out scenes",
  rendering: "rendering scenes",
  composing: "composing the final cut",
};

function useElapsedSeconds(sinceIso: string): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const started = new Date(sinceIso).getTime();
  return Math.max(0, Math.floor((now - started) / 1000));
}

function clock(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const ss = s.toString().padStart(2, "0");
  if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${ss}`;
  return `${m}:${ss}`;
}

/** Live, in-flight visualization shown in the hero while a job is non-terminal. */
export function RenderStage({ job }: RenderStageProps) {
  const elapsed = useElapsedSeconds(job.created_at);

  const total = job.progress.total ?? job.scenes.length;
  const doneCount = job.scenes.filter((s) => s.status === "done").length;
  // progress.current_scene is 1-based (the scene in flight); completed scenes = current_scene - 1.
  const completed =
    job.progress.current_scene != null
      ? Math.max(0, job.progress.current_scene - 1)
      : doneCount;
  const pct = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  const sceneNumber = Math.min(completed + 1, total);

  const eta =
    completed > 0 && total > completed && elapsed > 0
      ? Math.round((elapsed / completed) * (total - completed))
      : null;

  const stageLabel =
    (typeof job.progress.stage === "string" && job.progress.stage) ||
    STAGE_LABEL[job.status] ||
    "in flight";

  const activeScene =
    job.scenes.find((s) => s.status === "rendering") ??
    job.scenes.find((s) => s.status === "queued");

  const activeRender = job.status === "rendering" || job.status === "composing";
  const segments =
    total > 0
      ? Array.from({ length: total }, (_, i) => {
          const scene = job.scenes[i];
          if (scene?.status === "done") return "done";
          if (scene?.status === "rendering") return "current";
          if (i === completed && activeRender) return "current";
          return "pending";
        })
      : [];

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-6 px-6 text-center">
      <Orbit />

      <div className="space-y-2" aria-live="polite" aria-atomic="true">
        <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
          {total > 0 && job.status === "rendering"
            ? `rendering · scene ${sceneNumber} of ${total}`
            : stageLabel}
        </div>
        {activeScene && (
          <div className="mx-auto max-w-lg font-display text-2xl leading-snug text-foreground">
            {activeScene.narration}
          </div>
        )}
      </div>

      <div className="w-full max-w-md space-y-3">
        <div
          aria-hidden
          className="flex items-baseline justify-between font-mono text-[11px] tracking-[0.04em] text-muted-foreground"
        >
          <span>
            <span className="text-foreground tabular-nums">{completed}</span> / {total} scenes
          </span>
          <span className="tabular-nums">
            {eta != null && <span className="text-foreground">~{clock(eta)} left</span>}
            {eta != null && " · "}
            {clock(elapsed)} elapsed
          </span>
        </div>

        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          aria-label={`${stageLabel} — ${completed} of ${total} scenes done`}
          className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface-2"
        >
          <div
            aria-hidden
            className="absolute inset-y-0 left-0 rounded-full bg-accent transition-[width] duration-700 ease-out"
            style={{ width: `${pct}%`, boxShadow: "0 0 18px -2px var(--accent)" }}
          />
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[image:repeating-linear-gradient(45deg,transparent_0_8px,rgba(0,0,0,0.18)_8px_16px)]"
          />
        </div>

        {segments.length > 0 && segments.length <= 24 && (
          <div aria-hidden className="flex flex-wrap justify-center gap-1.5">
            {segments.map((state, i) => (
              <span
                key={i}
                className={`h-1 w-7 rounded-full ${state === "current" ? "animate-pulse-soft" : ""}`}
                style={{
                  background:
                    state === "done"
                      ? "var(--accent)"
                      : state === "current"
                        ? "color-mix(in oklch, var(--accent) 60%, transparent)"
                        : "color-mix(in oklch, var(--foreground) 12%, transparent)",
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Orbit() {
  return (
    <div className="relative size-28" aria-hidden>
      <span className="absolute inset-0 rounded-full border border-accent/35" />
      <span className="absolute inset-[16px] rounded-full border border-accent/20 animate-spin-rev" />
      <span className="absolute inset-[34px] rounded-full border border-info/30" />
      <span className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent animate-spin" />
      <span
        className="absolute inset-[48px] rounded-full bg-accent animate-pulse-soft"
        style={{ boxShadow: "0 0 40px -4px var(--accent)" }}
      />
    </div>
  );
}
