"use client";

import { History, Sparkles } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { CreateVideoForm } from "@/components/videos/CreateVideoForm";
import { RecentJobs } from "@/components/videos/RecentJobs";

export function HomeView() {
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-12 lg:py-20">
      <header className="relative mb-12 lg:mb-16">
        <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
          algo-reel · v0.1
        </div>
        <h1 className="mt-3 font-display text-5xl leading-[0.95] tracking-tight lg:text-7xl">
          Tutorials,{" "}
          <span className="font-display italic text-muted-foreground">rendered.</span>
        </h1>
        <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground">
          A prompt becomes a script becomes scenes becomes a video. Manim for code-driven motion,
          AI-image for stills + Ken Burns. Three minutes or less, under a dollar.
        </p>

        <div className="pointer-events-none absolute -top-8 right-0 hidden font-mono text-[10px] uppercase leading-relaxed tracking-[0.18em] text-muted-foreground/70 lg:block">
          <div>session bearer · localStorage</div>
          <div className="mt-1">sse · live progress</div>
          <div className="mt-1 text-accent/80">queue → script → render → compose</div>
        </div>
      </header>

      <section aria-labelledby="create">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-accent" />
              <CardTitle id="create" className="font-display">
                New video
              </CardTitle>
            </div>
            <CardDescription>
              The orchestrator drafts a script, fans out scenes, then composes the final mp4.
            </CardDescription>
          </CardHeader>
          <Separator />
          <CardContent className="pt-6">
            <CreateVideoForm />
          </CardContent>
        </Card>
      </section>

      <section aria-labelledby="recent" className="mt-16">
        <div className="mb-4 flex items-center gap-2">
          <History className="size-4 text-muted-foreground" />
          <h2
            id="recent"
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground"
          >
            recent jobs · this browser
          </h2>
        </div>
        <RecentJobs />
      </section>
    </div>
  );
}
