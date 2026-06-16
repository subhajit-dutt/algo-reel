"use client";

import { AlertOctagon, ArrowLeft, Ban, Download, RotateCw, Share2 } from "lucide-react";
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
import { JobHeader } from "@/components/videos/JobHeader";
import { SceneFilmstrip } from "@/components/videos/SceneFilmstrip";
import { VideoDetailSkeleton } from "@/components/videos/VideoDetailSkeleton";
import { VideoHero } from "@/components/videos/VideoHero";
import { useCancelJob } from "@/hooks/useCancelJob";
import { useJob } from "@/hooks/useJob";
import { useJobEvents } from "@/hooks/useJobEvents";
import { useResumeJob } from "@/hooks/useResumeJob";
import { ApiError } from "@/lib/api/client";
import { jobErrorReason } from "@/lib/utils";
import { type JobResponse, isTerminal } from "@/types/api";

interface VideoDetailViewProps {
  id: number;
}

const RESUMABLE = new Set<JobResponse["status"]>(["failed", "partially_failed"]);

export function VideoDetailView({ id }: VideoDetailViewProps) {
  const query = useJob(id);
  const job = query.data;
  const terminal = job ? isTerminal(job.status) : false;
  useJobEvents(id, Boolean(job && !terminal));

  useEffect(() => {
    if (!job) return;
    if (job.status === "failed") {
      toast.error(`Job #${job.id} failed`, {
        description: jobErrorReason(job.error),
        id: `job-${job.id}-failed`,
      });
    }
  }, [job]);

  if (query.isLoading) {
    return <VideoDetailSkeleton />;
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
        <AlertOctagon className="size-4 text-destructive" /> failed to load job #{id}
        <BackHome />
      </CenteredMessage>
    );
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10 lg:py-14">
      <div className="mb-6 flex items-center justify-between">
        <Link
          href="/"
          className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" /> all jobs
        </Link>
        <LiveIndicator terminal={terminal} />
      </div>

      <VideoHero job={job} />

      <JobHeader job={job} />

      {job.error && <ErrorPanel job={job} />}

      <SceneFilmstrip scenes={job.scenes} />

      <Footer job={job} terminal={terminal} />
    </div>
  );
}

function Footer({ job, terminal }: { job: JobResponse; terminal: boolean }) {
  return (
    <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-6">
      <div className="flex flex-wrap items-center gap-2.5">
        {job.output_url && (
          <Button asChild variant="primary">
            <a href={job.output_url} target="_blank" rel="noreferrer">
              <Download className="size-4" /> download mp4
            </a>
          </Button>
        )}
        <ShareButton />
        {RESUMABLE.has(job.status) && <ResumeButton id={job.id} />}
      </div>
      {!terminal && <CancelButton id={job.id} />}
    </footer>
  );
}

function ShareButton() {
  const onShare = async () => {
    await navigator.clipboard.writeText(window.location.href);
    toast.success("link copied to clipboard");
  };
  return (
    <Button variant="ghost" onClick={onShare}>
      <Share2 className="size-4" /> share link
    </Button>
  );
}

function ResumeButton({ id }: { id: number }) {
  const resume = useResumeJob(id);
  const onResume = async () => {
    try {
      await resume.mutateAsync();
      toast.success(`job #${id} resumed`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.info("job can't be resumed");
        return;
      }
      toast.error(err instanceof ApiError ? err.message : "resume failed");
    }
  };
  return (
    <Button variant="secondary" onClick={onResume} disabled={resume.isPending}>
      <RotateCw className="size-4" /> resume
    </Button>
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
      toast.error(err instanceof ApiError ? err.message : "cancel failed");
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

function ErrorPanel({ job }: { job: JobResponse }) {
  const error = job.error;
  if (!error) return null;
  return (
    <Card className="mt-6 rounded-2xl border-destructive/40 bg-destructive/5">
      <CardContent className="p-5">
        <div className="flex items-center gap-2">
          <AlertOctagon className="size-4 text-destructive" />
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-destructive">
            failure · {error.type}
          </span>
        </div>
        <div className="mt-2 space-y-1 text-sm">
          {error.reason && <ErrorLine label="reason" value={String(error.reason)} />}
          {error.message && <ErrorLine label="message" value={String(error.message)} />}
          {error.value !== undefined && <ErrorLine label="value" value={String(error.value)} />}
        </div>
      </CardContent>
    </Card>
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

function LiveIndicator({ terminal }: { terminal: boolean }) {
  if (terminal) {
    return <Badge tone="neutral">stream closed</Badge>;
  }
  return (
    <Badge tone="accent" className="gap-2">
      <span className="size-1.5 rounded-full bg-current animate-pulse-soft" />
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
