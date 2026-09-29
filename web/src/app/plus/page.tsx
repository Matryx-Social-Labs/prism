import type { Metadata } from "next";
import { social } from "@/lib/seo";
import { Suspense } from "react";
import { PlusPage } from "@/components/PlusPage";
import { fetchPlans } from "@/lib/billing";

const title = "Plus: professional readings and more questions";
const description = "The record stays free. Plus opens the professional readings of a story and more questions a day, answered from the whole story.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/plus" },
  ...social(title, description, "/plus"),
};

// Rendered per request: statically, useSearchParams (the `from` label) bailed
// the whole page out to the Suspense fallback, so the HTML a crawler received
// had no headline, no prices and no h1 (2026-09-21). The plans are read here
// too, so that HTML carries the prices; the page refreshes them in the browser.
export const dynamic = "force-dynamic";
export default async function Page() {
  const plans = await fetchPlans().catch(() => null);
  return (
    <Suspense fallback={null}>
      <PlusPage initialPlans={plans} />
    </Suspense>
  );
}
