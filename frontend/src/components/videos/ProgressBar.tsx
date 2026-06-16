import { cn } from "@/lib/utils";
import type { JobProgress } from "@/types/api";

interface ProgressBarProps {
  progress: JobProgress;
  className?: string;
}

export function ProgressBar({ progress, className }: ProgressBarProps) {
  const current = typeof progress.current_scene === "number" ? progress.current_scene : 0;
  const total = typeof progress.total === "number" && progress.total > 0 ? progress.total : 0;
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  const stage = typeof progress.stage === "string" ? progress.stage : null;

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-baseline justify-between font-mono text-xs">
        <span className="text-muted-foreground uppercase tracking-[0.14em]">
          {stage ?? "in flight"}
        </span>
        <span className="text-foreground tabular-nums">
          {total > 0 ? (
            <>
              <span className="text-accent">{current}</span>
              <span className="text-muted-foreground"> / </span>
              <span>{total}</span>
            </>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </span>
      </div>
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-surface">
        <div
          className="absolute inset-y-0 left-0 bg-accent transition-[width] duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
        <div className="absolute inset-0 bg-[image:repeating-linear-gradient(45deg,transparent_0_8px,rgba(255,255,255,0.04)_8px_16px)] pointer-events-none" />
      </div>
    </div>
  );
}
