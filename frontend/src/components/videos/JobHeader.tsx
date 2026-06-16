import { format } from "date-fns";

import { StatusBadge } from "@/components/videos/StatusBadge";
import { formatCost, formatRenderer } from "@/lib/utils";
import type { JobResponse } from "@/types/api";

interface JobHeaderProps {
  job: JobResponse;
}

export function JobHeader({ job }: JobHeaderProps) {
  return (
    <header className="mt-7 space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge status={job.status} />
        <span className="font-mono text-[13px] text-muted-foreground">
          job <span className="text-foreground">#{job.id.toString().padStart(5, "0")}</span>
        </span>
      </div>

      <h1 className="max-w-[46ch] font-display text-3xl leading-[1.08] tracking-tight lg:text-[2.6rem]">
        {job.user_prompt}
      </h1>

      <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-3 lg:grid-cols-6">
        <MetaCell label="renderer" value={formatRenderer(job.renderer)} />
        <MetaCell label="voice" value={job.voice} />
        <MetaCell label="target" value={`${job.duration_target_seconds}s`} />
        <MetaCell label="cost" value={formatCost(job.cost_usd)} accent />
        <MetaCell label="created" value={format(new Date(job.created_at), "MMM d · HH:mm")} />
        <MetaCell label="updated" value={format(new Date(job.updated_at), "MMM d · HH:mm")} />
      </dl>
    </header>
  );
}

function MetaCell({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-surface px-4 py-3">
      <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </dt>
      <dd
        className={`mt-1 font-mono text-sm tabular-nums ${accent ? "text-accent" : "text-foreground"}`}
      >
        {value}
      </dd>
    </div>
  );
}
