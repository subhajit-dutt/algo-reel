"use client";

import { AlertOctagon, Ban } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { RenderStage } from "@/components/videos/RenderStage";
import { StatusBadge } from "@/components/videos/StatusBadge";
import { VideoPlayer } from "@/components/videos/VideoPlayer";
import { formatRenderer, jobErrorReason } from "@/lib/utils";
import { type JobResponse, isTerminal } from "@/types/api";

interface VideoHeroProps {
  job: JobResponse;
}

const FRAME_BG =
  "radial-gradient(120% 120% at 50% 0%, var(--surface-2), var(--surface) 55%, #0d0f12 100%)";

const FRAME_SHADOW =
  "0 0 0 1px color-mix(in oklch, var(--accent) 12%, transparent)," +
  "0 30px 80px -40px rgba(0,0,0,0.9)," +
  "0 0 120px -55px color-mix(in oklch, var(--accent) 40%, transparent)";

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")";

/** Adaptive hero: video player when output exists, live render-stage while running,
 *  terminal panel for failed/cancelled jobs with no usable output. */
export function VideoHero({ job }: VideoHeroProps) {
  const terminal = isTerminal(job.status);
  const hasOutput = Boolean(job.output_url);

  return (
    <div
      className="relative aspect-video w-full animate-fade-in-up overflow-hidden rounded-2xl border border-border-strong"
      style={{ background: FRAME_BG, boxShadow: FRAME_SHADOW }}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10 opacity-[0.05] mix-blend-overlay"
        style={{ backgroundImage: GRAIN }}
      />

      <div className="absolute left-4 top-4 z-20">
        <StatusBadge status={job.status} />
      </div>
      <div className="absolute right-4 top-4 z-20">
        <Badge tone="neutral">{formatRenderer(job.renderer)}</Badge>
      </div>

      {hasOutput ? (
        <VideoPlayer src={job.output_url as string} />
      ) : terminal ? (
        <TerminalPanel job={job} />
      ) : (
        <RenderStage job={job} />
      )}
    </div>
  );
}

function TerminalPanel({ job }: { job: JobResponse }) {
  const cancelled = job.status === "cancelled";
  const Icon = cancelled ? Ban : AlertOctagon;
  const tone = cancelled ? "text-muted-foreground" : "text-destructive";
  const reason = jobErrorReason(job.error);

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-8 text-center">
      <Icon className={`size-9 ${tone}`} />
      <div className="font-display text-2xl text-foreground">
        {cancelled ? "Job cancelled" : "Render failed"}
      </div>
      {reason && (
        <p className="max-w-md font-mono text-xs leading-relaxed text-muted-foreground">{reason}</p>
      )}
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        no video was produced
      </p>
    </div>
  );
}
