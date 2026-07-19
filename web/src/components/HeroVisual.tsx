"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { HeroPoster } from "@/components/HeroPoster";

const PrismHero = dynamic(() => import("@/components/PrismHero"), {
  ssr: false,
  loading: () => <HeroPoster />,
});

// The 3D light-split scene runs in BOTH themes (its stage is a warm-toned
// panel, not page-colored). Only reduced-motion or no-WebGL clients get the
// static figure — and never download the three.js chunk.
export function HeroVisual() {
  const [mode, setMode] = useState<"pending" | "3d" | "poster">("pending");

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setMode("poster");
      return;
    }
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      setMode(gl ? "3d" : "poster");
    } catch {
      setMode("poster");
    }
  }, []);

  if (mode === "3d") return <PrismHero />;
  return <HeroPoster />;
}
