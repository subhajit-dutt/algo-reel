import { Shimmer } from "@/components/ui/shimmer";

/** Loading placeholder that mirrors the detail layout, so the page doesn't jump. */
export function VideoDetailSkeleton() {
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10 lg:py-14" aria-hidden>
      <div className="mb-6 flex items-center justify-between">
        <Shimmer className="h-4 w-24 rounded-md bg-surface" />
        <Shimmer className="h-6 w-20 rounded-full bg-surface" />
      </div>

      <Shimmer className="aspect-video w-full rounded-2xl bg-surface" />

      <div className="mt-7 space-y-4">
        <Shimmer className="h-5 w-40 rounded-md bg-surface" />
        <Shimmer className="h-9 w-3/4 rounded-md bg-surface" />
        <Shimmer className="h-9 w-1/2 rounded-md bg-surface" />
        <Shimmer className="h-16 w-full rounded-xl bg-surface" />
      </div>

      <div className="mt-10 grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Shimmer key={i} className="h-56 rounded-2xl bg-surface" />
        ))}
      </div>
    </div>
  );
}
