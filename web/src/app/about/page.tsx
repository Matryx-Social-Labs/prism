import type { Metadata } from "next";
import { Landing } from "@/components/Landing";

// The pitch at its permanent address. `/` shows the same page to a first
// visitor and sends everyone else to the chart (D5 revised), so the chart's
// promise line and the footer need somewhere the whole page always lives.
// Rendered per request so the proofs are today's, not the build's.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "About",
  description: "How Prism reads a story: every outlet's report of one event, gathered into one story you can re-read through a professional lens.",
};

export default async function AboutPage() {
  return Landing();
}
