import { apiFetch } from "@/lib/api/client";
import type { CreateVideoRequest, JobResponse } from "@/types/api";

export function createVideo(req: CreateVideoRequest): Promise<JobResponse> {
  return apiFetch<JobResponse>("/api/videos", { method: "POST", body: req });
}

export function getVideo(id: number, signal?: AbortSignal): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/api/videos/${id}`, { signal });
}

export function cancelVideo(id: number): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/api/videos/${id}`, { method: "DELETE" });
}

export function resumeVideo(id: number): Promise<JobResponse> {
  return apiFetch<JobResponse>(`/api/videos/${id}/resume`, { method: "POST" });
}
