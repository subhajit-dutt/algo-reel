import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import { cancelVideo } from "@/lib/api/videos";
import type { JobResponse } from "@/types/api";

import { jobQueryKey } from "./useJob";

export function useCancelJob(id: number) {
  const qc = useQueryClient();
  return useMutation<JobResponse, ApiError, void>({
    mutationFn: () => cancelVideo(id),
    onSuccess: (job) => {
      qc.setQueryData(jobQueryKey(id), job);
    },
  });
}
