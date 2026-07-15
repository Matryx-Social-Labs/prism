"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { HeroPoster } from "@/components/HeroPoster";

const PrismHero = dynamic(() => import("@/components/PrismHero"), {
  ssr: false,
  loading: () => <HeroPoster />,
});

// Decide BEFORE mounting: reduced-motion or WebGL-less clients render the
// static poster and never download the three.js chunk.
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
