import { cancelVideo } from "@/lib/api/videos";

import { useJobMutation } from "./useJobMutation";

export function useCancelJob(id: number) {
  return useJobMutation(id, cancelVideo);
}
