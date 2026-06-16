import { SceneCard } from "@/components/videos/SceneCard";
import type { SceneResponse } from "@/types/api";

interface SceneFilmstripProps {
  scenes: SceneResponse[];
}

export function SceneFilmstrip({ scenes }: SceneFilmstripProps) {
  const rendered = scenes.filter((s) => s.status === "done").length;

  return (
    <section className="mt-10">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          scenes
        </h2>
        <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
          {scenes.length > 0
            ? `${scenes.length} total · ${rendered} rendered`
            : "awaiting script"}
        </span>
      </div>

      {scenes.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-8 text-center font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground">
          no scenes yet — waiting for the script
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {scenes.map((scene, i) => (
            <SceneCard key={scene.id} scene={scene} index={i} />
          ))}
        </div>
      )}
    </section>
  );
}
