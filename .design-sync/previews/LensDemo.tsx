import { LensDemo } from "prism-web";

// The landing-page lens-switch moment: one headline, three lens tabs.
// Falls back to its built-in curated example when the live API is absent —
// which is exactly what the static card shows.
export const Demo = () => (
  <div style={{ maxWidth: 680, padding: 16 }}>
    <LensDemo />
  </div>
);
