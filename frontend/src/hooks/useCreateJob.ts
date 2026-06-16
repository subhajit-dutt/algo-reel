import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import { createVideo } from "@/lib/api/videos";
import { pushRecentId } from "@/lib/history/recent";
import type { CreateVideoRequest, JobResponse } from "@/types/api";

import { jobQueryKey } from "./useJob";

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation<JobResponse, ApiError, CreateVideoRequest>({
    mutationFn: createVideo,
    onSuccess: (job) => {
      pushRecentId(job.id);
      qc.setQueryData(jobQueryKey(job.id), job);
    },
  });
}
