"use client";

import { Play } from "lucide-react";
import { useRef } from "react";

import { Shimmer } from "@/components/ui/shimmer";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/videos/StatusBadge";
import { formatDuration, truncate } from "@/lib/utils";
import type { SceneResponse } from "@/types/api";

interface SceneCardProps {
  scene: SceneResponse;
  index: number;
}

const THUMB_GRID =
  "linear-gradient(color-mix(in oklch, var(--accent) 12%, transparent) 1px, transparent 1px)," +
  "linear-gradient(90deg, color-mix(in oklch, var(--accent) 12%, transparent) 1px, transparent 1px)";

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function SceneCard({ scene, index }: SceneCardProps) {
  return (
    <div
      className="animate-fade-in-up overflow-hidden rounded-2xl border border-border bg-surface transition-[transform,border-color,background] duration-200 hover:-translate-y-0.5 hover:border-border-strong hover:bg-surface-2"
      style={{ animationDelay: `${Math.min(index, 8) * 45}ms` }}
    >
      <SceneThumb scene={scene} />
      <div className="space-y-2.5 p-3.5">
        <StatusBadge status={scene.status} />
        <Tooltip>
          <TooltipTrigger asChild>
            <p className="cursor-help text-sm leading-snug text-foreground">
              {truncate(scene.narration, 96)}
            </p>
          </TooltipTrigger>
          <TooltipContent>
            <span className="leading-relaxed">{scene.narration}</span>
          </TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <p className="flex cursor-help gap-2 font-mono text-[11px] leading-relaxed text-muted-foreground">
              <span aria-hidden className="text-accent">
                ▹
              </span>
              <span>{truncate(scene.visual_prompt, 64)}</span>
            </p>
          </TooltipTrigger>
          <TooltipContent>
            <span className="leading-relaxed">{scene.visual_prompt}</span>
          </TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}

function SceneThumb({ scene }: { scene: SceneResponse }) {
  const ref = useRef<HTMLVideoElement>(null);
  const ready = scene.status === "done" && Boolean(scene.output_url);
  const rendering = scene.status === "rendering";

  // Hover preview is a decorative progressive enhancement: the scene's narration and
  // visual prompt are fully available as text below, so the clip carries no extra info.
  const onEnter = () => {
    if (prefersReducedMotion()) return;
    void ref.current?.play();
  };
  const onLeave = () => {
    const v = ref.current;
    if (!v) return;
    v.pause();
    v.currentTime = 0;
  };

  return (
    <div
      className="group relative aspect-video border-b border-border bg-surface-sunken"
      onMouseEnter={ready ? onEnter : undefined}
      onMouseLeave={ready ? onLeave : undefined}
    >
      {ready ? (
        <video
          ref={ref}
          src={scene.output_url as string}
          muted
          playsInline
          loop
          preload="metadata"
          aria-hidden
          tabIndex={-1}
          className="h-full w-full object-cover"
        />
      ) : (
        <span
          aria-hidden
          className="absolute inset-0"
          style={{
            backgroundImage: THUMB_GRID,
            backgroundSize: "24px 24px",
            opacity: rendering ? 0.4 : 0.25,
            maskImage: "radial-gradient(80% 80% at 50% 50%, #000, transparent)",
            WebkitMaskImage: "radial-gradient(80% 80% at 50% 50%, #000, transparent)",
          }}
        />
      )}

      {rendering && <Shimmer className="absolute inset-0" />}

      <span className="absolute left-2.5 top-2 font-mono text-[11px] text-muted-foreground">
        {scene.index.toString().padStart(2, "0")}
      </span>

      {ready && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 grid place-items-center opacity-80 transition-opacity group-hover:opacity-0"
        >
          <span className="grid size-9 place-items-center rounded-full border border-white/25 bg-black/50 text-white backdrop-blur-sm">
            <Play className="ml-0.5 size-3.5 fill-current" />
          </span>
        </span>
      )}

      <span className="absolute bottom-2 right-2.5 rounded-md bg-black/55 px-1.5 py-0.5 font-mono text-[10.5px] text-foreground">
        {formatDuration(scene.duration_seconds)}
      </span>
    </div>
  );
}
