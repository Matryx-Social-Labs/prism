"use client";

import { useEffect, useState } from "react";

type Choice = "system" | "light" | "dark";
const KEY = "prism.theme"; // the one ThemeToggle and the layout's first-paint script read
const CHOICES: { value: Choice; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];
// .p-seg keys its pressed look on aria-selected (tabs); a setting is a radio group.
const ON = { background: "var(--surface)", color: "var(--ink)", boxShadow: "var(--shadow-1), 0 0 0 1px var(--line)" } as const;

/**
 * Theme as a setting (Design System v2 · You): System follows the device, which
 * the header's toggle cannot return to. Fires "prism-theme" so a toggle that
 * listens can re-read its icon.
 */
export function ThemeChoice() {
  const [choice, setChoice] = useState<Choice>("system");
  useEffect(() => {
    const t = localStorage.getItem(KEY);
    setChoice(t === "light" || t === "dark" ? t : "system");
  }, []);

  function pick(next: Choice) {
    setChoice(next);
    const root = document.documentElement;
    if (next === "system") {
      localStorage.removeItem(KEY);
      delete root.dataset.theme;
    } else {
      localStorage.setItem(KEY, next);
      root.dataset.theme = next;
    }
    window.dispatchEvent(new Event("prism-theme"));
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <span id="theme-label" className="p-field__label">Theme</span>
      <div className="p-seg" role="radiogroup" aria-labelledby="theme-label">
        {CHOICES.map((c) => (
          <button key={c.value} type="button" className="p-hit" role="radio" aria-checked={choice === c.value} onClick={() => pick(c.value)} style={choice === c.value ? ON : undefined}>
            {c.label}
          </button>
        ))}
      </div>
    </div>
  );
}
