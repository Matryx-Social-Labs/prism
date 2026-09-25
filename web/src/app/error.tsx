"use client";

import { SystemPage } from "@/components/ui";

// A page that threw while rendering. The digest is Next's reference for the
// server log, printed so a reader can quote it; reset() re-renders the segment.
export default function RouteError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <SystemPage kind="error" reference={error.digest} onRetry={reset} />;
}
