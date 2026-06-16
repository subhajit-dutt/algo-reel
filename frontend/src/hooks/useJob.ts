import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/client";
import { getVideo } from "@/lib/api/videos";
import type { JobResponse } from "@/types/api";

export const jobQueryKey = (id: number) => ["job", id] as const;

export function useJob(id: number, enabled = true): UseQueryResult<JobResponse, ApiError> {
  return useQuery<JobResponse, ApiError>({
    queryKey: jobQueryKey(id),
    queryFn: ({ signal }) => getVideo(id, signal),
    enabled,
    retry: (failureCount, err) => {
      if (err instanceof ApiError && (err.status === 401 || err.status === 404)) return false;
      return failureCount < 2;
    },
    staleTime: 5_000,
  });
}
