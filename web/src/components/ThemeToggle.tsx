"use client";

import { useEffect, useState } from "react";
import { MoonIcon, SunIcon } from "@/components/icons";

type Mode = "light" | "dark" | null;

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeToggle() {
  const [mode, setMode] = useState<Mode>(null);

  // Re-read when the theme setting on You changes it (it fires "prism-theme").
  useEffect(() => {
    const read = () => setMode((localStorage.getItem("prism.theme") as Mode) ?? null);
    read();
    window.addEventListener("prism-theme", read);
    return () => window.removeEventListener("prism-theme", read);
  }, []);

  function toggle() {
    const effectiveDark = mode ? mode === "dark" : systemPrefersDark();
    const next: Mode = effectiveDark ? "light" : "dark";
    setMode(next);
    localStorage.setItem("prism.theme", next);
    document.documentElement.dataset.theme = next;
  }

  // Known only after mount: the server cannot see the reader's preference, so the first
  // client render must match it (no hydration mismatch) and the icon settles in an effect.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const effectiveDark = mounted && (mode ? mode === "dark" : systemPrefersDark());

  return (
    // The icon shows where a tap takes you (Design System v2 · ThemeToggle): a moon on paper, a sun in the dark.
    <button type="button" onClick={toggle} aria-label={effectiveDark ? "Use light theme" : "Use dark theme"} className="icon-btn">
      {effectiveDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
