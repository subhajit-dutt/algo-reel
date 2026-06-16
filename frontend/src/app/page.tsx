"use client";

import { usePathname } from "next/navigation";

import { HomeView } from "@/views/HomeView";
import { VideoDetailView } from "@/views/VideoDetailView";

// Single client-side router. output:'export' forbids dynamic [id] routes, so
// app/static.py falls back to index.html for /videos/{id}/ and we read the
// path here.
const VIDEO_RE = /^\/videos\/(\d+)\/?$/;

export default function Page() {
  const pathname = usePathname();
  const match = pathname.match(VIDEO_RE);
  if (match) {
    const id = Number(match[1]);
    if (Number.isFinite(id) && id > 0) {
      return <VideoDetailView id={id} />;
    }
  }
  return <HomeView />;
}
