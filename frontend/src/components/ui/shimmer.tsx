import { cn } from "@/lib/utils";

const SHIMMER_GRADIENT =
  "linear-gradient(100deg, transparent 30%, rgba(255,255,255,0.06) 50%, transparent 70%)";

/** Animated sweeping highlight — loading skeletons and in-progress placeholders.
 *  Decorative; always aria-hidden. Compose with bg/size/position via className. */
export function Shimmer({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("animate-shimmer", className)}
      style={{ backgroundImage: SHIMMER_GRADIENT, backgroundSize: "200% 100%" }}
    />
  );
}
