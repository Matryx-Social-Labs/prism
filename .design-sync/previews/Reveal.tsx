import { Reveal } from "prism-web";

// Scroll-reveal wrapper (IntersectionObserver adds the .reveal transition).
// In previews the content is in-viewport, so it renders revealed.
export const CardGrid = () => (
  <div style={{ display: "grid", gap: 12, maxWidth: 480, padding: 16 }}>
    {["Politics", "Markets", "Technology"].map((label) => (
      <Reveal key={label}>
        <div
          className="rounded-2xl border p-5"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
        >
          <p className="font-semibold">{label}</p>
          <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
            Stories from the {label.toLowerCase()} desk, revealed on scroll.
          </p>
        </div>
      </Reveal>
    ))}
  </div>
);

export const AsSection = () => (
  <Reveal as="section" className="p-5">
    <h2 className="text-xl font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
      Same story. Different stakes.
    </h2>
    <p className="mt-1 text-sm" style={{ color: "var(--ink-muted)" }}>
      Sections fade and rise into view as the reader scrolls.
    </p>
  </Reveal>
);
