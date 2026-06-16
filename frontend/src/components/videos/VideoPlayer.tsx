"use client";

import { Play } from "lucide-react";
import { useRef, useState } from "react";

interface VideoPlayerProps {
  src: string;
}

const POSTER_BG =
  "radial-gradient(60% 80% at 30% 30%, color-mix(in oklch, var(--info) 28%, transparent), transparent 60%)," +
  "radial-gradient(70% 90% at 75% 70%, color-mix(in oklch, var(--accent) 20%, transparent), transparent 55%)," +
  "var(--surface-sunken)";

const POSTER_GRID =
  "linear-gradient(color-mix(in oklch, var(--accent) 13%, transparent) 1px, transparent 1px)," +
  "linear-gradient(90deg, color-mix(in oklch, var(--accent) 13%, transparent) 1px, transparent 1px)";

/** Browser-native player inside the hero frame, with a custom poster + play overlay
 *  shown until first playback. */
export function VideoPlayer({ src }: VideoPlayerProps) {
  const ref = useRef<HTMLVideoElement>(null);
  const [started, setStarted] = useState(false);

  const start = () => {
    setStarted(true);
    void ref.current?.play();
  };

  return (
    <div className="absolute inset-0">
      <video
        ref={ref}
        src={src}
        controls={started}
        playsInline
        preload="metadata"
        onPlay={() => setStarted(true)}
        className="h-full w-full bg-black object-contain"
      />

      {!started && (
        <button
          type="button"
          onClick={start}
          aria-label="Play video"
          className="group absolute inset-0 grid place-items-center"
          style={{ background: POSTER_BG }}
        >
          <span
            aria-hidden
            className="absolute inset-0"
            style={{
              backgroundImage: POSTER_GRID,
              backgroundSize: "46px 46px",
              opacity: 0.5,
              maskImage: "radial-gradient(70% 70% at 50% 45%, #000, transparent)",
              WebkitMaskImage: "radial-gradient(70% 70% at 50% 45%, #000, transparent)",
            }}
          />
          <span
            className="relative z-10 grid size-[4.5rem] place-items-center rounded-full bg-accent text-accent-foreground transition-transform duration-200 group-hover:scale-105"
            style={{
              boxShadow:
                "0 0 0 10px color-mix(in oklch, var(--accent) 16%, transparent), 0 0 60px -8px var(--accent)",
            }}
          >
            <Play className="ml-1 size-7 fill-current" />
          </span>
        </button>
      )}
    </div>
  );
}
