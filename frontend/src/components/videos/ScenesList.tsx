import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { StatusBadge } from "@/components/videos/StatusBadge";
import { formatDuration, truncate } from "@/lib/utils";
import type { SceneResponse } from "@/types/api";

interface ScenesListProps {
  scenes: SceneResponse[];
}

export function ScenesList({ scenes }: ScenesListProps) {
  if (scenes.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border p-6 text-center font-mono text-xs text-muted-foreground uppercase tracking-[0.14em]">
        no scenes yet — waiting for script
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface">
          <tr className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
            <th className="px-3 py-2 w-12 text-right">#</th>
            <th className="px-3 py-2">narration</th>
            <th className="px-3 py-2">visual prompt</th>
            <th className="px-3 py-2 w-20 text-right">dur</th>
            <th className="px-3 py-2 w-32">status</th>
          </tr>
        </thead>
        <tbody>
          {scenes.map((s) => (
            <tr key={s.id} className="border-t border-border/60 hover:bg-surface/40">
              <td className="px-3 py-2.5 font-mono text-xs text-muted-foreground tabular-nums text-right">
                {s.index.toString().padStart(2, "0")}
              </td>
              <td className="px-3 py-2.5">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="cursor-help">{truncate(s.narration, 80)}</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <span className="leading-relaxed">{s.narration}</span>
                  </TooltipContent>
                </Tooltip>
              </td>
              <td className="px-3 py-2.5 text-muted-foreground">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="cursor-help">{truncate(s.visual_prompt, 60)}</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <span className="leading-relaxed">{s.visual_prompt}</span>
                  </TooltipContent>
                </Tooltip>
              </td>
              <td className="px-3 py-2.5 text-right font-mono text-xs tabular-nums">
                {formatDuration(s.duration_seconds)}
              </td>
              <td className="px-3 py-2.5">
                <StatusBadge status={s.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
