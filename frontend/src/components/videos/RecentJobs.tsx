"use client";

import { formatDistanceToNowStrict } from "date-fns";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/videos/StatusBadge";
import { useJob } from "@/hooks/useJob";
import { ApiError } from "@/lib/api/client";
import { getRecentIds, removeRecentId } from "@/lib/history/recent";
import { cn, formatCost, truncate } from "@/lib/utils";
import type { JobResponse } from "@/types/api";

export function RecentJobs() {
  const [ids, setIds] = useState<number[]>([]);

  useEffect(() => {
    const sync = () => setIds(getRecentIds());
    sync();
    window.addEventListener("algoreel:recent-changed", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("algoreel:recent-changed", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (ids.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center font-mono text-[11px] text-muted-foreground uppercase tracking-[0.14em]">
        no jobs yet — your history will appear here
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {ids.map((id) => (
        <RecentJobRow key={id} id={id} />
      ))}
    </ul>
  );
}

function RecentJobRow({ id }: { id: number }) {
  const { data, error, isLoading } = useJob(id);

  useEffect(() => {
    if (error instanceof ApiError && error.status === 404) {
      removeRecentId(id);
    }
  }, [error, id]);

  if (error instanceof ApiError && error.status === 404) return null;

  return (
    <li>
      <Link href={`/videos/${id}/`} className="block group">
        <Card
          className={cn(
            "flex items-center gap-4 p-3 transition-[border,background] duration-150",
            "group-hover:border-border-strong group-hover:bg-surface-2",
          )}
        >
          <span className="font-mono text-[11px] text-muted-foreground tabular-nums w-16 shrink-0">
            #{id.toString().padStart(5, "0")}
          </span>
          <div className="min-w-0 flex-1">
            {isLoading ? (
              <div className="font-mono text-xs text-muted-foreground">loading…</div>
            ) : data ? (
              <JobSummary job={data} />
            ) : (
              <div className="font-mono text-xs text-destructive">error</div>
            )}
          </div>
          <ArrowRight className="size-4 shrink-0 text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-foreground" />
        </Card>
      </Link>
    </li>
  );
}

function JobSummary({ job }: { job: JobResponse }) {
  const ago = formatDistanceToNowStrict(new Date(job.created_at), { addSuffix: true });
  return (
    <div className="flex flex-col gap-1">
      <div className="text-sm leading-snug text-foreground">{truncate(job.user_prompt, 88)}</div>
      <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
        <StatusBadge status={job.status} />
        <span>{job.renderer.replace("_", " · ")}</span>
        <span>·</span>
        <span>{job.duration_target_seconds}s</span>
        <span>·</span>
        <span>{formatCost(job.cost_usd)}</span>
        <span className="ml-auto">{ago}</span>
      </div>
    </div>
  );
}
