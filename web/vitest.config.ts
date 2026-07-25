import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  // No @vitejs/plugin-react: it exists for Fast Refresh, which tests don't use,
  // and it drags in a second copy of vite whose Plugin type collides with the
  // app's under `tsc --noEmit`. esbuild handles the JSX on its own — tsconfig
  // sets jsx:"preserve" for Next, so point it at the automatic runtime here.
  esbuild: { jsx: "automatic" },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Next's own build output and e2e dirs are not vitest's business.
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
  resolve: {
    // Mirror the "@/*" -> "src/*" alias from tsconfig.json.
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
