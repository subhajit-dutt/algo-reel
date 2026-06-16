import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import { subscribeJobEvents } from "@/lib/sse/subscribe";
import { type JobResponse, type ProgressEvent, isTerminal } from "@/types/api";

import { jobQueryKey } from "./useJob";

export function useJobEvents(id: number, enabled: boolean): void {
  const qc = useQueryClient();

  useEffect(() => {
    if (!enabled) return;

    const controller = subscribeJobEvents(id, {
      onEvent: (ev: ProgressEvent) => {
        qc.setQueryData<JobResponse>(jobQueryKey(id), (prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            status: ev.status,
            progress: ev.progress ?? prev.progress,
            error: ev.error ?? prev.error,
            updated_at: ev.ts,
          };
        });

        if (isTerminal(ev.status)) {
          // Refetch the canonical snapshot once the job terminates so we pick up
          // any fields the SSE delta doesn't carry (output_url, scenes, cost_usd).
          qc.invalidateQueries({ queryKey: jobQueryKey(id) });
        }
      },
    });

    return () => controller.abort();
  }, [id, enabled, qc]);
}
