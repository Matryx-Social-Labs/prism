import { ThemeToggle } from "prism-web";

// The adaptive light/dark switch from the app header. Persists the choice
// to localStorage and stamps data-theme on <html>.
export const Toggle = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 12, padding: 16 }}>
    <span style={{ fontSize: 13, color: "var(--ink-muted)" }}>Theme</span>
    <ThemeToggle />
  </div>
);
