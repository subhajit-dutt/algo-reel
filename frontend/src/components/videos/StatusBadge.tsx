import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { JobStatus, SceneStatus } from "@/types/api";

type AnyStatus = JobStatus | SceneStatus;

const TONE: Record<AnyStatus, NonNullable<BadgeProps["tone"]>> = {
  queued: "neutral",
  scripting: "info",
  script_ready: "info",
  rendering: "warning",
  composing: "warning",
  done: "success",
  failed: "destructive",
  cancelled: "neutral",
  partially_failed: "destructive",
};

const LABEL: Partial<Record<AnyStatus, string>> = {
  script_ready: "script ready",
  partially_failed: "partial fail",
};

const PULSE_STATUSES = new Set<AnyStatus>(["scripting", "rendering", "composing", "queued"]);

interface StatusBadgeProps {
  status: AnyStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const label = LABEL[status] ?? status;
  const pulsing = PULSE_STATUSES.has(status);
  return (
    <Badge tone={TONE[status]} className="gap-2">
      <span className={`size-1.5 rounded-full bg-current ${pulsing ? "animate-pulse-soft" : ""}`} />
      {label}
    </Badge>
  );
}
