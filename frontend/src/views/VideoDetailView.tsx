"use client";

import { format } from "date-fns";
import { AlertOctagon, ArrowLeft, Ban, Download, Loader2, Radio } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ProgressBar } from "@/components/videos/ProgressBar";
import { ScenesList } from "@/components/videos/ScenesList";
import { StatusBadge } from "@/components/videos/StatusBadge";
import { useCancelJob } from "@/hooks/useCancelJob";
import { useJob } from "@/hooks/useJob";
import { useJobEvents } from "@/hooks/useJobEvents";
import { ApiError } from "@/lib/api/client";
import { formatCost } from "@/lib/utils";
import { type JobResponse, isTerminal } from "@/types/api";

interface VideoDetailViewProps {
  id: number;
}

export function VideoDetailView({ id }: VideoDetailViewProps) {
  const query = useJob(id);
  const job = query.data;
  const terminal = job ? isTerminal(job.status) : false;
  useJobEvents(id, Boolean(job && !terminal));

  useEffect(() => {
    if (!job) return;
    if (job.status === "failed") {
      toast.error(`Job #${job.id} failed`, {
        description: job.error?.reason ?? job.error?.message ?? job.error?.type,
        id: `job-${job.id}-failed`,
      });
    }
  }, [job]);

  if (query.isLoading) {
    return (
      <CenteredMessage>
        <Loader2 className="size-4 animate-spin" /> loading job #{id}…
      </CenteredMessage>
    );
  }
  if (query.error instanceof ApiError && query.error.status === 404) {
    return (
      <CenteredMessage>
        <AlertOctagon className="size-4 text-destructive" /> job #{id} not found
        <BackHome />
      </CenteredMessage>
    );
  }
  if (!job) {
    return (
      <CenteredMessage>
        <AlertOctagon className="size-4 text-destructive" />
        failed to load
        <BackHome />
      </CenteredMessage>
    );
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10 lg:py-14">
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" /> all jobs
        </Link>
        <LiveIndicator terminal={terminal} />
      </div>

      <header className="space-y-4">
        <div className="flex flex-wrap items-baseline gap-3">
          <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            job
          </span>
          <span className="font-mono text-2xl tabular-nums text-foreground">
            #{job.id.toString().padStart(5, "0")}
          </span>
          <StatusBadge status={job.status} />
        </div>

        <h1 className="font-display text-3xl leading-tight tracking-tight lg:text-4xl">
          {job.user_prompt}
        </h1>

        <MetaGrid job={job} />
      </header>

      {!terminal && (
        <section className="mt-10">
          <Card>
            <CardContent className="space-y-4 p-5">
              <ProgressBar progress={job.progress} />
            </CardContent>
          </Card>
        </section>
      )}

      {job.error && (
        <section className="mt-6">
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-5">
              <div className="flex items-center gap-2">
                <AlertOctagon className="size-4 text-destructive" />
                <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-destructive">
                  failure · {job.error.type}
                </span>
              </div>
              <div className="mt-2 space-y-1 text-sm">
                {job.error.reason && (
                  <ErrorLine label="reason" value={String(job.error.reason)} />
                )}
                {job.error.message && (
                  <ErrorLine label="message" value={String(job.error.message)} />
                )}
                {job.error.value !== undefined && (
                  <ErrorLine label="value" value={String(job.error.value)} />
                )}
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      <section className="mt-10">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            scenes
          </h2>
          <span className="font-mono text-[11px] text-muted-foreground tabular-nums">
            {job.scenes.length} total
          </span>
        </div>
        <ScenesList scenes={job.scenes} />
      </section>

      <Separator className="my-10" />

      <footer className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {job.output_url && (
            <Button asChild variant="secondary">
              <a href={job.output_url} target="_blank" rel="noreferrer">
                <Download className="size-4" /> download mp4
              </a>
            </Button>
          )}
        </div>
        {!terminal && <CancelButton id={id} />}
      </footer>
    </div>
  );
}

function MetaGrid({ job }: { job: JobResponse }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 border-y border-border py-4 sm:grid-cols-4">
      <MetaCell label="renderer" value={job.renderer} />
      <MetaCell label="voice" value={job.voice} />
      <MetaCell label="target" value={`${job.duration_target_seconds}s`} />
      <MetaCell label="cost" value={formatCost(job.cost_usd)} />
      <MetaCell
        label="created"
        value={format(new Date(job.created_at), "MMM d · HH:mm:ss")}
        wide
      />
      <MetaCell
        label="updated"
        value={format(new Date(job.updated_at), "MMM d · HH:mm:ss")}
        wide
      />
    </dl>
  );
}

function MetaCell({ label, value, wide }: { label: string; value: string; wide?: boolean }) {
  return (
    <div className={wide ? "sm:col-span-2" : ""}>
      <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 font-mono text-sm tabular-nums text-foreground">{value}</dd>
    </div>
  );
}

function ErrorLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3 font-mono text-xs">
      <span className="w-16 shrink-0 uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </span>
      <span className="text-foreground">{value}</span>
    </div>
  );
}

function CancelButton({ id }: { id: number }) {
  const cancel = useCancelJob(id);

  const onConfirm = async () => {
    try {
      await cancel.mutateAsync();
      toast.success(`job #${id} cancelled`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.info("already terminal — nothing to cancel");
        return;
      }
      const msg = err instanceof ApiError ? err.message : "cancel failed";
      toast.error(msg);
    }
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" disabled={cancel.isPending}>
          <Ban className="size-4" /> cancel job
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Cancel job #{id}?</AlertDialogTitle>
          <AlertDialogDescription>
            The worker stops at its next checkpoint. Scenes already rendered are retained for 24h.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep running</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Cancel job</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function LiveIndicator({ terminal }: { terminal: boolean }) {
  if (terminal) {
    return (
      <Badge tone="neutral" className="gap-2">
        <Radio className="size-3" /> stream closed
      </Badge>
    );
  }
  return (
    <Badge tone="accent" className="gap-2">
      <span
        className="size-1.5 rounded-full bg-current"
        style={{ animation: "algo-pulse 1.6s ease-in-out infinite" }}
      />
      live · sse
    </Badge>
  );
}

function CenteredMessage({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-md flex-col items-center justify-center gap-3 px-6 py-12 text-center font-mono text-xs text-muted-foreground">
      {children}
    </div>
  );
}

function BackHome() {
  return (
    <Button asChild variant="secondary" size="sm" className="mt-2">
      <Link href="/">
        <ArrowLeft className="size-4" /> home
      </Link>
    </Button>
  );
}
