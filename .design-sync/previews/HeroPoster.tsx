import { HeroPoster } from "prism-web";

// The static beam→prism→spectrum brand figure (fallback for the 3D hero).
// currentColor drives the beam strokes — set an explicit color at the wrapper.
// The style block pins the settled animation state (same rules the app applies
// under prefers-reduced-motion) so the static card shows the drawn beams.
export const Poster = () => (
  <div style={{ color: "var(--ink)", maxWidth: 560, padding: "24px 16px" }}>
    <style>{`.beam-in, .beam-out { stroke-dashoffset: 0; animation: none; }`}</style>
    <p
      style={{
        textAlign: "center",
        fontFamily: "var(--font-display), serif",
        fontSize: 22,
        fontWeight: 600,
        marginBottom: 4,
      }}
    >
      One event. Every angle.
    </p>
    <HeroPoster />
  </div>
);
