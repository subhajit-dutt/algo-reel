import "./globals.css";

import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";

import { TokenGate } from "@/components/auth/TokenGate";

import { Providers } from "./providers";

const geist = Geist({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-mono",
});

const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "algo-reel — illustrative video generator",
  description:
    "Turn a prompt into a short illustrative video. Manim and AI-image renderers, ≤3 min, under a dollar.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geist.variable} ${geistMono.variable} ${instrumentSerif.variable}`}
    >
      <body className="relative min-h-screen">
        <Providers>
          <TokenGate>
            <div className="relative z-10">{children}</div>
          </TokenGate>
        </Providers>
      </body>
    </html>
  );
}
