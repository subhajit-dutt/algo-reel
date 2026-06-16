import { fetchEventSource, type EventSourceMessage } from "@microsoft/fetch-event-source";

import { API_BASE } from "@/config";
import { clearToken, getToken } from "@/lib/auth/token";
import type { ProgressEvent } from "@/types/api";

export interface SubscribeHandlers {
  onEvent: (ev: ProgressEvent) => void;
  onError?: (err: unknown) => void;
  onClose?: () => void;
}

class FatalSSEError extends Error {}

export function subscribeJobEvents(jobId: number, handlers: SubscribeHandlers): AbortController {
  const controller = new AbortController();
  const token = getToken();
  if (!token) {
    handlers.onError?.(new Error("missing bearer token"));
    return controller;
  }

  fetchEventSource(`${API_BASE}/api/videos/${jobId}/events`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}`, Accept: "text/event-stream" },
    signal: controller.signal,
    openWhenHidden: true,
    async onopen(res) {
      if (res.ok && res.headers.get("content-type")?.includes("text/event-stream")) return;
      if (res.status === 401) {
        clearToken();
        throw new FatalSSEError("unauthorized");
      }
      throw new FatalSSEError(`SSE open failed: ${res.status}`);
    },
    onmessage(msg: EventSourceMessage) {
      if (!msg.data) return;
      const parsed = JSON.parse(msg.data) as ProgressEvent;
      handlers.onEvent(parsed);
    },
    onerror(err) {
      if (err instanceof FatalSSEError) throw err;
      handlers.onError?.(err);
      // Let the library retry transient network failures (default behavior).
    },
    onclose() {
      handlers.onClose?.();
    },
  }).catch((err) => {
    if (controller.signal.aborted) return;
    handlers.onError?.(err);
  });

  return controller;
}
