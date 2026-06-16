import { useMutation, useQueryClient } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { JobResponse } from "@/types/api";

import { jobQueryKey } from "./useJob";

/** Shared mutation for actions that act on a job by id and return the updated job
 *  (cancel, resume). Writes the fresh job back into the query cache on success. */
export function useJobMutation(id: number, action: (id: number) => Promise<JobResponse>) {
  const qc = useQueryClient();
  return useMutation<JobResponse, ApiError, void>({
    mutationFn: () => action(id),
    onSuccess: (job) => {
      qc.setQueryData(jobQueryKey(id), job);
    },
  });
}
