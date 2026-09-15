import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // .font-display = the structural voice: masthead labels, the strip, section heads, big numbers
        display: ["var(--font-display)", "sans-serif"],
        // .font-mono everywhere = the provenance voice (DESIGN.md)
        mono: ["var(--font-mono)", "ui-monospace", "Menlo", "monospace"],
      },
      colors: {
        severity: {
          critical: "#dc2626",
          high: "#ea580c",
          medium: "#d97706",
          low: "#65a30d",
        },
      },
    },
  },
  plugins: [],
};

export default config;
