"use client";

import "./globals.css";
import { SystemPage } from "@/components/ui";

// The root layout itself failed, so this page brings its own <html>. The
// next/font faces live in that layout and are absent here: the voices fall
// back to their stacks (Georgia, the system sans), which is enough for one line.
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body>
        <SystemPage kind="error" reference={error.digest} onRetry={reset} />
      </body>
    </html>
  );
}
