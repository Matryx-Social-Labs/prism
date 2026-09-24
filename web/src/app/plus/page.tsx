import type { Metadata } from "next";
import { Suspense } from "react";
import { PlusPage } from "@/components/PlusPage";

export const metadata: Metadata = {
  title: "Plus",
  description: "The evidence stays free. Plus is for the reader who asks more of it: answers from the whole story, 100 questions a day.",
  alternates: { canonical: "/plus" },
};

// Rendered per request: statically, useSearchParams (the `from` label) bailed
// the whole page out to the Suspense fallback, so the HTML a crawler received
// had no headline, no prices and no h1 (2026-09-21).
export const dynamic = "force-dynamic";
export default function Page() {
  return (
    <Suspense fallback={null}>
      <PlusPage />
    </Suspense>
  );
}
