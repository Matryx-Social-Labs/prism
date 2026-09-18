"use client";

import { useEffect, useState } from "react";
import { MoonIcon, SunIcon } from "@/components/icons";

type Mode = "light" | "dark" | null;

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeToggle() {
  const [mode, setMode] = useState<Mode>(null);

  useEffect(() => {
    setMode((localStorage.getItem("prism.theme") as Mode) ?? null);
  }, []);

  function toggle() {
    const effectiveDark = mode ? mode === "dark" : systemPrefersDark();
    const next: Mode = effectiveDark ? "light" : "dark";
    setMode(next);
    localStorage.setItem("prism.theme", next);
    document.documentElement.dataset.theme = next;
  }

  const effectiveDark = mode ? mode === "dark" : systemPrefersDark();

  return (
    <button onClick={toggle} aria-label="Toggle color theme" className="icon-btn">
      {effectiveDark ? <MoonIcon /> : <SunIcon />}
    </button>
  );
}
