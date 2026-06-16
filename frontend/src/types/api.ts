// Wire types — mirror docs/apis/videos.md exactly. Hand-maintained on purpose.

export type Renderer = "manim" | "ai_image";

export type DurationTarget = 30 | 60 | 180;

export type JobStatus =
  | "queued"
  | "scripting"
  | "script_ready"
  | "rendering"
  | "composing"
  | "done"
  | "failed"
  | "cancelled"
  | "partially_failed";

export type SceneStatus = "queued" | "rendering" | "done" | "failed" | "cancelled";

export type SSEEventName = "snapshot" | "progress" | "transition" | "failed" | "done";

export interface JobError {
  type: string;
  reason?: string;
  message?: string;
  value?: string | number;
  [k: string]: unknown;
}

export interface JobProgress {
  current_scene?: number;
  total?: number;
  stage?: string;
  [k: string]: unknown;
}

export interface SceneResponse {
  id: number;
  index: number;
  narration: string;
  visual_prompt: string;
  // wire type is a string-encoded decimal (e.g. "15.00"); keep as string and parse on use.
  duration_seconds: string;
  status: SceneStatus;
  output_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobResponse {
  id: number;
  user_prompt: string;
  renderer: Renderer;
  voice: string;
  duration_target_seconds: DurationTarget;
  status: JobStatus;
  progress: JobProgress;
  output_url: string | null;
  cost_usd: string;
  error: JobError | null;
  scenes: SceneResponse[];
  created_at: string;
  updated_at: string;
}

export interface CreateVideoRequest {
  prompt: string;
  renderer: Renderer;
  duration_target: DurationTarget;
  voice: string;
}

export interface ProgressEvent {
  event: SSEEventName;
  job_id: number;
  status: JobStatus;
  progress: JobProgress;
  scene_id: number | null;
  error: JobError | null;
  ts: string;
}

export const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set<JobStatus>([
  "done",
  "failed",
  "cancelled",
  "partially_failed",
]);

export const isTerminal = (status: JobStatus): boolean => TERMINAL_STATUSES.has(status);
