import { resumeVideo } from "@/lib/api/videos";

import { useJobMutation } from "./useJobMutation";

export function useResumeJob(id: number) {
  return useJobMutation(id, resumeVideo);
}
