"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { HeroPoster } from "@/components/HeroPoster";

const PrismHero = dynamic(() => import("@/components/PrismHero"), {
  ssr: false,
  loading: () => <HeroPoster />,
});

function currentTheme(): "light" | "dark" {
  const attr = document.documentElement.dataset.theme;
  if (attr === "dark" || attr === "light") return attr;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

// The 3D light-split scene needs a dark stage, so it only runs in the dark
// theme (with WebGL and motion allowed). Everyone else — light theme,
// reduced motion, no WebGL — gets the theme-native animated figure and
// never downloads the three.js chunk. Theme toggles swap the hero live.
export function HeroVisual() {
  const [mode, setMode] = useState<"pending" | "3d" | "poster">("pending");

  useEffect(() => {
    function decide() {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        setMode("poster");
        return;
      }
      if (currentTheme() !== "dark") {
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
    }
    decide();
    const observer = new MutationObserver(decide);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", decide);
    return () => {
      observer.disconnect();
      media.removeEventListener("change", decide);
    };
  }, []);

  if (mode === "3d") return <PrismHero />;
  return <HeroPoster />;
}
