"use client";

import { useEffect, useState } from "react";

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
    <button
      onClick={toggle}
      aria-label="Toggle color theme"
      className="flex h-8 w-8 items-center justify-center rounded-full border transition hover:opacity-70"
      style={{ borderColor: "var(--line)" }}
    >
      {/* Stroked glyphs in currentColor: the emoji sun rendered in amber, which
          on this chrome reads as the general lens speaking. */}
      {effectiveDark ? (
        <svg aria-hidden width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
        </svg>
      ) : (
        <svg aria-hidden width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      )}
    </button>
  );
}
