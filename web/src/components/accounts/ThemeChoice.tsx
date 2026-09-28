"use client";

import { useEffect, useId, useState } from "react";

type Choice = "system" | "light" | "dark";
const KEY = "prism.theme"; // the one ThemeToggle and the layout's first-paint script read
const CHOICES: { value: Choice; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];
// .p-seg keys its pressed look on aria-selected (tabs); a setting is a radio group.
const ON = { background: "var(--surface)", color: "var(--ink)", boxShadow: "var(--shadow-1), 0 0 0 1px var(--line)" } as const;

const stored = (): Choice => {
  const t = localStorage.getItem(KEY);
  return t === "light" || t === "dark" ? t : "system";
};

/**
 * Theme as a setting (Design System v2 · You): System follows the device, which
 * the header's toggle cannot return to.
 */
export function ThemeChoice() {
  const id = useId();
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <span id={id} className="p-field__label">Theme</span>
      <ThemeSeg labelledBy={id} />
    </div>
  );
}

/**
 * System · Light · Dark, labelled by the caller: the You page's Theme row, and the
 * footer's Appearance row (the phone bar's theme control, screens/PhoneBar.html).
 * Fires "prism-theme" and re-reads on it, so this and the header's toggle never disagree.
 */
export function ThemeSeg({ labelledBy }: { labelledBy: string }) {
  const [choice, setChoice] = useState<Choice>("system");
  useEffect(() => {
    const read = () => setChoice(stored());
    read();
    window.addEventListener("prism-theme", read);
    return () => window.removeEventListener("prism-theme", read);
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
    <div className="p-seg" role="radiogroup" aria-labelledby={labelledBy}>
      {CHOICES.map((c) => (
        <button key={c.value} type="button" className="p-hit" role="radio" aria-checked={choice === c.value} onClick={() => pick(c.value)} style={choice === c.value ? ON : undefined}>
          {c.label}
        </button>
      ))}
    </div>
  );
}
