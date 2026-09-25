import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // .font-display = the record voice (Newsreader + per-script serifs), tokens --font-record
        display: ["var(--font-record)"],
        // .font-mono everywhere = the provenance voice, tokens --font-mono (Geist Mono)
        mono: ["var(--font-mono)"],
        // .font-read = the reading voice (Anek), tokens --font-read
        read: ["var(--font-read)"],
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
